import logging

from django.utils import timezone
from rest_framework import filters, mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from core.audit import log_action
from core.scoping import PlantScopedQuerysetMixin
from . import services

logger = logging.getLogger(__name__)
from .models import AuditFinding, AuditGroup, AuditPrep, AuditProgram, EvidenceItem
from .permissions import AuditPrepPermission
from .serializers import (
    AuditFindingSerializer,
    AuditGroupSerializer,
    AuditPrepSerializer,
    AuditProgramSerializer,
    EvidenceItemSerializer,
)


def _require_all_group_sites(user, group) -> None:
    """Le scritture sull'audit comune toccano tutti i siti del gruppo: servono
    tutti (chi ne gestisce uno solo non decide per l'altro)."""
    from django.utils.translation import gettext as _
    from rest_framework.exceptions import PermissionDenied

    from core.scoping import user_can_access_plant

    for plant_id in group.preps.values_list("plant_id", flat=True):
        if not user_can_access_plant(user, plant_id):
            raise PermissionDenied(_(
                "Per modificare un audit multi-sito serve l'accesso a tutti i suoi siti."
            ))


def _serve_evidence_file(evidence, user, entity):
    """Download del rapporto ufficiale collegato all'audit (l'accesso è quello
    all'audit, già verificato da get_object)."""
    import os

    from django.core.files.storage import default_storage
    from django.http import FileResponse, Http404
    from django.utils.translation import gettext as _

    if not evidence or evidence.deleted_at or not evidence.file_path:
        raise Http404(_("Nessun rapporto allegato a questo audit."))
    path = evidence.file_path
    if ".." in path or path.startswith("/") or not default_storage.exists(path):
        raise Http404(_("File non trovato nello storage."))
    log_action(
        user=user, action_code="audit_prep.official_report.downloaded", level="L2",
        entity=entity, payload={"evidence_id": str(evidence.pk)},
    )
    return FileResponse(default_storage.open(path, "rb"), as_attachment=True,
                        filename=os.path.basename(path))


def _get_scoped(qs, pk):
    """Oggetto `pk` dentro il queryset già filtrato per perimetro, o None
    (anche per id malformati)."""
    import uuid

    try:
        return qs.filter(pk=uuid.UUID(str(pk))).first()
    except (TypeError, ValueError):
        return None


def _second_party_no_checklist(prep=None) -> str:
    from django.utils.translation import gettext as _

    if prep is not None and prep.audit_type == "interno":
        return _(
            "Audit interno condotto da un consulente esterno: i punti di verifica sono "
            "quelli del consulente, la checklist dei controlli non si usa. Registra i "
            "rilievi del consulente come finding."
        )
    return _(
        "Audit di seconda parte: i punti di verifica sono quelli del cliente, "
        "la checklist dei controlli non si usa. Registra i rilievi dell'auditor come finding."
    )


def _validation_response(exc):
    return Response({"error": exc.messages[0] if getattr(exc, "messages", None) else str(exc)}, status=400)


class AuditPrepViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = AuditPrep.objects.select_related("framework", "report_evidence", "group").prefetch_related(
        "group__preps__plant",
    )
    serializer_class = AuditPrepSerializer
    permission_classes = [AuditPrepPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["plant", "status", "framework", "audit_type"]
    search_fields = ["title", "auditor_name", "requesting_party"]
    plant_field = "plant"

    def perform_create(self, serializer):
        # L'audit singolo (non lanciato da un programma) copre tutti i controlli:
        # il campione ha senso solo nei programmi pluriennali a più step.
        extra = {} if serializer.validated_data.get("audit_program") else {"coverage_type": "full"}
        instance = serializer.save(created_by=self.request.user, **extra)
        services.finalize_new_prep(instance, self.request.user)

    @staticmethod
    def _sync_program(prep):
        """Riallinea il programma annuale allo stato reale del prep.

        Serve a ogni via che cambia lo stato — PATCH generica, completamento,
        annullamento — altrimenti l'audit resta «in corso» nel programma anche
        dopo essere stato chiuso: era il caso delle azioni dedicate, che non
        passano da `perform_update`.
        """
        if not prep.audit_program_id:
            return
        from .services import sync_program_completion
        try:
            sync_program_completion(prep.audit_program)
        except Exception as exc:
            logger.warning(
                "audit_prep: sync_program_completion fallita per prep %s: %s",
                prep.pk, exc,
            )

    def perform_update(self, serializer):
        # Audit multi-sito: i dati comuni si cambiano dall'audit comune, che li
        # riporta su tutti i siti (altrimenti i siti divergerebbero).
        if serializer.instance.group_id:
            from django.utils.translation import gettext as _
            from rest_framework.exceptions import ValidationError as DRFValidationError

            touched = set(serializer.validated_data) & set(services.GROUP_SHARED_FIELDS)
            if touched:
                raise DRFValidationError({"error": _(
                    "Questo audit fa parte di un audit multi-sito: i dati comuni si "
                    "modificano dall'audit comune."
                )})
        instance = serializer.save()
        if "audit_type" in serializer.validated_data:
            services.sync_pdca_audit_subtype([instance], self.request.user)
        self._sync_program(instance)
        log_action(
            user=self.request.user,
            action_code="audit_prep.updated",
            level="L2",
            entity=instance,
            payload={"status": instance.status},
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        open_findings = instance.findings.filter(
            status__in=["open", "in_response"]
        ).count()
        if open_findings > 0:
            return Response(
                {
                    "error": (
                        f"Impossibile cancellare: ci sono {open_findings} finding aperti. "
                        f"Chiudi o archivia i finding prima di procedere."
                    )
                },
                status=400,
            )
        instance.soft_delete()
        log_action(
            user=request.user,
            action_code="audit_prep.auditprep.deleted",
            level="L2",
            entity=instance,
            payload={
                "title": instance.title,
                "reason": str(request.data.get("reason", ""))[:200],
            },
        )
        return Response(status=204)

    @action(detail=True, methods=["get", "post", "delete"], url_path="report-file")
    def report_file(self, request, pk=None):
        """
        GET    /audit-prep/audit-preps/<id>/report-file/  → scarica il rapporto ufficiale
               (anche quando l'evidenza sta su un altro sito dell'audit multi-sito).
        POST   multipart: file, title (opz.) → allega il rapporto dell'auditor/ente
               (evidenza "report"); per un audit multi-sito vale per tutti i siti.
        DELETE → scollega il rapporto (l'evidenza resta archiviata).
        """
        from django.core.exceptions import ValidationError as DjangoValidationError
        from django.utils.translation import gettext as _

        prep = self.get_object()
        if request.method == "GET":
            return _serve_evidence_file(prep.report_evidence, request.user, prep)
        group = prep.group
        if group:
            _require_all_group_sites(request.user, group)
        if request.method == "DELETE":
            if group:
                services.detach_group_report(group, request.user)
            else:
                services.detach_official_report(prep, request.user)
            return Response(status=204)
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response({"error": _("Il file del rapporto è obbligatorio.")}, status=400)
        try:
            if group:
                services.attach_group_report(group, uploaded_file, request.user,
                                             title=request.data.get("title", ""))
            else:
                services.attach_official_report(prep, uploaded_file, request.user,
                                                title=request.data.get("title", ""))
        except DjangoValidationError as exc:
            return _validation_response(exc)
        prep.refresh_from_db()
        return Response(AuditPrepSerializer(prep, context={"request": request}).data, status=201)

    @action(detail=True, methods=["post"], url_path="annulla")
    def annulla(self, request, pk=None):
        """Annulla un AuditPrep avviato per errore."""
        instance = self.get_object()
        reason = request.data.get("reason", "")
        if not reason or len(reason.strip()) < 10:
            return Response(
                {
                    "error": "Motivo annullamento obbligatorio (min 10 caratteri)"
                },
                status=400,
            )
        instance.findings.filter(
            status__in=["open", "in_response"]
        ).update(status="closed")
        instance.status = "archiviato"
        instance.save(update_fields=["status", "updated_at"])
        closed_reminders = services.close_prep_reminders(
            instance, request.user,
            reason=f"Audit prep «{instance.title}» annullato: {reason.strip()}",
        )
        self._sync_program(instance)
        log_action(
            user=request.user,
            action_code="audit_prep.auditprep.cancelled",
            level="L2",
            entity=instance,
            payload={
                "title": instance.title,
                "reason": reason.strip()[:200],
                "reminders_closed": closed_reminders,
            },
        )
        return Response({
            "ok": True,
            "status": "archiviato",
            "reminders_closed": closed_reminders,
        })

    @action(detail=True, methods=["get"])
    def readiness(self, request, pk=None):
        audit_prep = self.get_object()
        if not audit_prep.uses_checklist:
            return Response({"id": str(audit_prep.id), "readiness_score": None})
        score = services.calc_readiness_score(audit_prep)
        return Response({"id": str(audit_prep.id), "readiness_score": score})

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        """Marca un AuditPrep come completato."""
        prep = self.get_object()
        open_majors = prep.findings.filter(
            finding_type="major_nc", status__in=["open", "in_response"]
        ).count()
        if open_majors > 0:
            return Response(
                {"error": f"Non puoi completare con {open_majors} Major NC aperti."},
                status=400,
            )
        prep.status = "completato"
        prep.save(update_fields=["status", "updated_at"])
        # Il prep è concluso: i suoi promemoria non hanno più motivo di esistere
        # e il programma annuale va riallineato, altrimenti l'audit resta «in
        # corso» pur essendo chiuso.
        closed_reminders = services.close_prep_reminders(
            prep, request.user, reason=f"Audit prep «{prep.title}» completato."
        )
        self._sync_program(prep)
        log_action(
            user=request.user,
            action_code="audit_prep.auditprep.completed",
            level="L1", entity=prep,
            payload={"title": prep.title, "reminders_closed": closed_reminders},
        )
        return Response({
            "ok": True,
            "status": "completato",
            "reminders_closed": closed_reminders,
        })

    @action(detail=True, methods=["post"], url_path="sync-controls")
    def sync_controls(self, request, pk=None):
        """Allinea il prep ai controlli previsti dall'espansione gerarchica
        del framework. Tipico caso d'uso: prep TISAX_L3 creato prima della fix
        contiene solo i controlli L3 — questa azione aggiunge gli `EvidenceItem`
        per i controlli L2 (e PROTO->L2+L3) ancora mancanti, senza toccare
        quelli gia' presenti. Idempotente.
        """
        from .framework_hierarchy import expand_tisax
        from .services import seed_evidence_items_for_prep

        prep = self.get_object()
        if prep.status == "archiviato":
            return Response(
                {"error": "Prep archiviato: sincronizzazione non disponibile."},
                status=400,
            )
        if not prep.uses_checklist:
            return Response({"error": _second_party_no_checklist(prep)}, status=400)

        fw_code = prep.framework.code if prep.framework_id else None
        if not fw_code:
            return Response(
                {"error": "Prep senza framework: impossibile espandere la gerarchia."},
                status=400,
            )

        expanded = expand_tisax([fw_code])
        if len(expanded) <= 1:
            return Response({
                "ok": True,
                "added": 0,
                "frameworks_requested": [fw_code],
                "frameworks_expanded": expanded,
                "note": "Framework non gerarchico: nessun controllo da aggiungere.",
            })

        added = seed_evidence_items_for_prep(
            prep,
            framework_codes=[fw_code],
            coverage_type=prep.coverage_type or "campione",
            user=request.user,
            only_missing=True,
        )

        log_action(
            user=request.user,
            action_code="audit_prep.evidence.synced",
            level="L2",
            entity=prep,
            payload={
                "frameworks_requested": [fw_code],
                "frameworks_expanded": expanded,
                "items_added": added,
            },
        )
        return Response({
            "ok": True,
            "added": added,
            "frameworks_requested": [fw_code],
            "frameworks_expanded": expanded,
        })

    @action(detail=True, methods=["post"], url_path="auto-validate")
    def auto_validate(self, request, pk=None):
        """Esegue la validazione automatica del prep: valuta evidenze/documenti
        per ogni control_instance, aggiorna lo stato degli evidence_item e
        apre i finding minor_nc per gli item mancante/scaduto.
        Idempotente: rilanciata non duplica i finding gia' auto-generati aperti."""
        from .validation import auto_validate_prep
        prep = self.get_object()
        if not prep.uses_checklist:
            return Response({"error": _second_party_no_checklist(prep)}, status=400)
        if prep.status == "archiviato":
            return Response(
                {"error": "Prep archiviato: validazione automatica non disponibile."},
                status=400,
            )
        summary = auto_validate_prep(prep, request.user)
        return Response({"ok": True, **summary})

    @action(detail=True, methods=["get"], url_path="report")
    def report(self, request, pk=None):
        """Scarica relazione HTML dell'AuditPrep."""
        from .services import generate_audit_report
        from django.http import HttpResponse
        prep = self.get_object()
        html = generate_audit_report(prep)
        filename = (
            f"AuditReport_{prep.audit_date or 'draft'}_"
            f"{timezone.now().strftime('%Y%m%d')}.html"
        )
        log_action(
            user=request.user,
            action_code="audit_prep.report_downloaded",
            level="L2", entity=prep,
            payload={"filename": filename},
        )
        resp = HttpResponse(html, content_type="text/html; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp


class AuditGroupViewSet(
    PlantScopedQuerysetMixin,
    mixins.ListModelMixin, mixins.RetrieveModelMixin,
    mixins.CreateModelMixin, mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Audit multi-sito (non organizzazione): creazione con un AuditPrep per
    sito e modifica dei dati comuni, riportati su tutti i siti. Visibile a chi
    accede ad almeno uno dei siti; le scritture richiedono tutti i siti.
    L'eliminazione avviene per singolo audit di sito."""
    queryset = AuditGroup.objects.select_related("framework", "report_evidence").prefetch_related(
        "preps__plant",
    )
    serializer_class = AuditGroupSerializer
    permission_classes = [AuditPrepPermission]
    plant_field = "preps__plant"

    def perform_create(self, serializer):
        from django.core.exceptions import ValidationError as DjangoValidationError
        from rest_framework.exceptions import PermissionDenied, ValidationError as DRFValidationError
        from django.utils.translation import gettext as _

        from core.scoping import user_can_access_plant

        data = dict(serializer.validated_data)
        plants = data.pop("plants")
        for plant in plants:
            if not user_can_access_plant(self.request.user, plant):
                raise PermissionDenied(_("Accesso negato per questo sito."))
        try:
            serializer.instance = services.create_audit_group(user=self.request.user, plants=plants, **data)
        except DjangoValidationError as exc:
            raise DRFValidationError({"error": exc.messages[0]}) from exc

    def perform_update(self, serializer):
        _require_all_group_sites(self.request.user, serializer.instance)
        data = dict(serializer.validated_data)
        data.pop("plants", None)
        serializer.instance = services.update_audit_group(serializer.instance, self.request.user, **data)


class EvidenceItemViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = EvidenceItem.objects.all()
    serializer_class = EvidenceItemSerializer
    permission_classes = [AuditPrepPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["audit_prep", "status"]
    plant_field = "audit_prep__plant"

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="audit_prep.evidence.create",
            level="L2",
            entity=instance,
            payload={
                "id": str(instance.id),
                "audit_prep_id": str(instance.audit_prep_id),
            },
        )


class AuditFindingViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = AuditFinding.objects.select_related(
        "audit_prep__plant", "control_instance__control",
        "pdca_cycle", "closed_by", "lesson_learned",
    )
    serializer_class = AuditFindingSerializer
    permission_classes = [AuditPrepPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["audit_prep", "finding_type", "status", "audit_prep__plant"]
    search_fields = ["title", "description"]
    plant_field = "audit_prep__plant"

    def perform_create(self, serializer):
        data = self.request.data
        # Resolve audit_date string to date object if needed
        audit_date_raw = data.get("audit_date")
        if isinstance(audit_date_raw, str):
            from dateutil import parser as dateparser
            try:
                audit_date = dateparser.parse(audit_date_raw).date()
            except Exception:
                audit_date = timezone.localdate()
        else:
            audit_date = audit_date_raw or timezone.localdate()

        prep = serializer.validated_data["audit_prep"]
        kwargs = dict(
            finding_type=data.get("finding_type"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            audit_date=audit_date,
            user=self.request.user,
            control_instance=serializer.validated_data.get("control_instance"),
            auditor_name=data.get("auditor_name", ""),
        )
        # Rilievo comune a tutti i siti di un audit multi-sito: un finding per
        # sito (il controllo è per sito, quindi non si riporta sugli altri).
        if str(data.get("apply_to_group", "")).lower() in ("true", "1") and prep.group_id:
            from django.core.exceptions import ValidationError as DjangoValidationError
            from rest_framework.exceptions import ValidationError as DRFValidationError

            _require_all_group_sites(self.request.user, prep.group)
            kwargs["control_instance"] = None
            # common_pdca → un solo PDCA di organizzazione per tutti i siti.
            common_pdca = str(data.get("common_pdca", "")).lower() in ("true", "1")
            try:
                finding = services.open_group_finding(prep, common_pdca=common_pdca, **kwargs)[0]
            except DjangoValidationError as exc:
                raise DRFValidationError({"error": exc.messages[0]}) from exc
        else:
            finding = services.open_finding(audit_prep=prep, **kwargs)
        # Attach the created instance so DRF can return it
        serializer.instance = finding

    def perform_update(self, serializer):
        """Del finding si correggono solo i testi (refusi): tipo, audit, date e
        stato passano dalle azioni dedicate (PDCA, chiusura)."""
        from django.core.exceptions import ValidationError as DjangoValidationError
        from django.utils.translation import gettext as _
        from rest_framework.exceptions import ValidationError as DRFValidationError

        data = dict(serializer.validated_data)
        other = set(data) - set(services.FINDING_EDITABLE_FIELDS)
        if other:
            raise DRFValidationError({"error": _(
                "Del finding si modificano solo titolo, descrizione, causa radice e azione correttiva."
            )})
        finding = serializer.instance
        # rilievo comune: titolo e descrizione cambiano su tutti i siti
        if finding.common_key and set(data) & set(services.FINDING_SHARED_TEXT) and finding.audit_prep.group_id:
            _require_all_group_sites(self.request.user, finding.audit_prep.group)
        try:
            serializer.instance = services.update_finding_text(finding, self.request.user, **data)
        except DjangoValidationError as exc:
            raise DRFValidationError({"error": exc.messages[0]}) from exc

    def get_queryset(self):
        qs = super().get_queryset()
        # ?without_pdca=true → finding ancora senza PDCA (per il collegamento);
        # di default solo quelli aperti, con ?include_closed=true anche i chiusi
        # (collegamento a posteriori dello storico).
        params = self.request.query_params
        if params.get("without_pdca", "").lower() == "true":
            qs = qs.filter(pdca_cycle__isnull=True)
            if params.get("include_closed", "").lower() != "true":
                qs = qs.exclude(status__in=["closed", "accepted_by_auditor"])
        return qs

    @action(detail=True, methods=["post"], url_path="open-pdca")
    def open_pdca(self, request, pk=None):
        """POST /findings/<id>/open-pdca/ {title?, descrizione?} → PDCA già collegato."""
        from django.core.exceptions import ValidationError as DjangoValidationError

        finding = self.get_object()
        try:
            services.open_pdca_for_finding(
                finding, request.user,
                title=request.data.get("title", ""), descrizione=request.data.get("descrizione", ""),
            )
        except DjangoValidationError as exc:
            return _validation_response(exc)
        finding.refresh_from_db()
        return Response(AuditFindingSerializer(finding).data, status=201)

    @action(detail=True, methods=["post"], url_path="open-common-pdca")
    def open_common_pdca(self, request, pk=None):
        """POST /findings/<id>/open-common-pdca/ {title?, descrizione?} → PDCA di
        organizzazione collegato al rilievo comune su tutti i siti."""
        from django.core.exceptions import ValidationError as DjangoValidationError

        finding = self.get_object()
        try:
            _cycle, result = services.open_common_pdca(
                finding, request.user,
                title=request.data.get("title", ""), descrizione=request.data.get("descrizione", ""),
            )
        except DjangoValidationError as exc:
            return _validation_response(exc)
        finding.refresh_from_db()
        return Response({**AuditFindingSerializer(finding).data, "common_link": result}, status=201)

    @action(detail=True, methods=["post"], url_path="link-pdca")
    def link_pdca(self, request, pk=None):
        """POST /findings/<id>/link-pdca/ {pdca_cycle} → collega un PDCA esistente."""
        from django.core.exceptions import ValidationError as DjangoValidationError
        from django.utils.translation import gettext as _

        from apps.pdca.models import PdcaCycle
        from core.scoping import scope_queryset_by_plant

        finding = self.get_object()
        cycle = _get_scoped(
            scope_queryset_by_plant(PdcaCycle.objects.all(), request.user, plant_field="plant"),
            request.data.get("pdca_cycle"),
        )
        if cycle is None:
            return Response({"error": _("PDCA non trovato.")}, status=404)
        try:
            # PDCA di organizzazione → il rilievo comune su tutti i siti.
            if cycle.plant_id is None:
                result = services.link_common_findings_to_pdca(finding, cycle, request.user)
            else:
                result = None
                services.link_finding_to_pdca(finding, cycle, request.user)
        except DjangoValidationError as exc:
            return _validation_response(exc)
        finding.refresh_from_db()
        return Response({**AuditFindingSerializer(finding).data, "common_link": result})

    @action(detail=True, methods=["post"], url_path="replace-pdca")
    def replace_pdca(self, request, pk=None):
        """POST /findings/<id>/replace-pdca/ {pdca_cycle, reason} → sostituisce il PDCA."""
        from django.core.exceptions import ValidationError as DjangoValidationError
        from django.utils.translation import gettext as _

        from apps.pdca.models import PdcaCycle
        from core.scoping import scope_queryset_by_plant

        finding = self.get_object()
        cycle = _get_scoped(
            scope_queryset_by_plant(PdcaCycle.objects.all(), request.user, plant_field="plant"),
            request.data.get("pdca_cycle"),
        )
        if cycle is None:
            return Response({"error": _("PDCA non trovato.")}, status=404)
        reason = request.data.get("reason", "")
        try:
            if cycle.plant_id is None:
                if not reason or len(reason.strip()) < 10:
                    raise DjangoValidationError(_("Motivo obbligatorio (minimo 10 caratteri)."))
                result = services.link_common_findings_to_pdca(finding, cycle, request.user, reason)
            else:
                result = None
                services.replace_finding_pdca(finding, cycle, request.user, reason)
        except DjangoValidationError as exc:
            return _validation_response(exc)
        finding.refresh_from_db()
        return Response({**AuditFindingSerializer(finding).data, "common_link": result})

    @action(detail=True, methods=["post"], url_path="close-with-pdca")
    def close_with_pdca(self, request, pk=None):
        """POST /findings/<id>/close-with-pdca/ → chiude con evidenza e note del PDCA chiuso."""
        from django.core.exceptions import ValidationError as DjangoValidationError

        finding = self.get_object()
        try:
            services.close_finding_with_pdca(finding, request.user)
        except DjangoValidationError as exc:
            return _validation_response(exc)
        finding.refresh_from_db()
        return Response(AuditFindingSerializer(finding).data)

    @action(detail=True, methods=["post"], url_path="unlink-pdca")
    def unlink_pdca(self, request, pk=None):
        """POST /findings/<id>/unlink-pdca/ {reason} → scollega (motivo obbligatorio)."""
        from django.core.exceptions import ValidationError as DjangoValidationError

        finding = self.get_object()
        try:
            services.unlink_finding_from_pdca(finding, request.user, request.data.get("reason", ""))
        except DjangoValidationError as exc:
            return _validation_response(exc)
        finding.refresh_from_db()
        return Response(AuditFindingSerializer(finding).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        from .services import close_finding
        from apps.documents.models import Evidence
        from django.core.exceptions import ValidationError

        finding = self.get_object()
        notes = request.data.get("closure_notes", "")
        evidence_id = request.data.get("evidence_id")
        evidence = None
        if evidence_id:
            evidence = Evidence.objects.filter(pk=evidence_id).first()
        try:
            finding = close_finding(finding, request.user, notes, evidence)
            return Response({"ok": True, "status": finding.status})
        except ValidationError as e:
            return _validation_response(e)


class AuditProgramViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = AuditProgram.objects.select_related("plant", "framework", "approved_by")
    serializer_class = AuditProgramSerializer
    permission_classes = [AuditPrepPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["plant", "framework", "year", "status"]
    search_fields = ["title"]
    plant_field = "plant"

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="audit_prep.program.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "year": instance.year},
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.soft_delete()
        log_action(
            user=request.user,
            action_code="audit_prep.program.deleted",
            level="L2",
            entity=instance,
            payload={"title": instance.title, "year": instance.year},
        )
        return Response(status=204)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        from django.utils import timezone
        program = self.get_object()
        program.status = "approvato"
        program.approved_by = request.user
        program.approved_at = timezone.now()
        program.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        log_action(
            user=request.user,
            action_code="audit_prep.program.approved",
            level="L1",
            entity=program,
            payload={"year": program.year},
        )
        return Response({"ok": True, "status": program.status})

    @action(detail=True, methods=["post"], url_path="add-audit")
    def add_audit(self, request, pk=None):
        """Aggiunge o aggiorna un audit pianificato nel JSON array."""
        program = self.get_object()
        audit_entry = request.data.get("audit", {})
        if not audit_entry:
            return Response({"error": "Dati audit mancanti"}, status=400)
        planned = list(program.planned_audits)
        planned.append(audit_entry)
        program.planned_audits = planned
        program.save(update_fields=["planned_audits", "updated_at"])
        return Response({"ok": True, "planned_audits": program.planned_audits})

    @action(detail=False, methods=["post"], url_path="suggest")
    def suggest(self, request):
        """Genera piano annuale suggerito dal sistema."""
        from .services import suggest_audit_plan
        from apps.controls.models import Framework
        from apps.plants.models import Plant
        plant_id = request.data.get("plant")
        framework_codes = request.data.get("framework_codes", [])
        year = int(request.data.get("year", 2026))
        coverage_type = request.data.get("coverage_type", "campione")
        plant = Plant.objects.filter(pk=plant_id).first()
        frameworks = Framework.objects.filter(code__in=framework_codes)
        if not plant or not frameworks.exists():
            return Response({"error": "plant e framework_codes obbligatori"}, status=400)
        # Il piano è generato direttamente dal plant nel body (non dal queryset
        # scoped del viewset): serve accesso al sito (sweep 2026-06-12).
        from core.scoping import require_plant_access
        require_plant_access(request.user, plant)
        plan = suggest_audit_plan(plant, frameworks, year, coverage_type)
        return Response({"suggested_plan": plan})

    @action(detail=True, methods=["post"], url_path="launch-audit")
    def launch_audit(self, request, pk=None):
        """Lancia un AuditPrep da un audit pianificato."""
        from .services import launch_audit_from_program
        program = self.get_object()
        audit_id = request.data.get("audit_id")
        audit_entry = next(
            (a for a in program.planned_audits if a.get("id") == audit_id), None
        )
        if not audit_entry:
            return Response({"error": "Audit non trovato nel programma"}, status=404)
        if audit_entry.get("audit_prep_id"):
            return Response({"error": "Questo audit ha già un AuditPrep collegato"}, status=400)
        prep = launch_audit_from_program(program, audit_entry, request.user)
        return Response({
            "ok": True,
            "audit_prep_id": str(prep.pk),
            "controls_count": prep.evidence_items.count(),
        })

    @action(detail=True, methods=["post"], url_path="update-audit")
    def update_audit(self, request, pk=None):
        """Aggiorna un audit pianificato nel JSON."""
        program = self.get_object()
        audit_id = request.data.get("audit_id")
        updates = request.data.get("updates", {})
        audits = list(program.planned_audits)
        ALLOWED = ["title", "planned_date", "auditor_type", "auditor_name",
                   "scope_domains", "coverage_type", "notes", "status"]
        for a in audits:
            if a.get("id") == audit_id:
                for k, v in updates.items():
                    if k in ALLOWED:
                        a[k] = v
                break
        program.planned_audits = audits
        program.save(update_fields=["planned_audits", "updated_at"])
        return Response({"ok": True, "planned_audits": audits})

    @action(detail=True, methods=["post"], url_path="sync-completion")
    def sync_completion(self, request, pk=None):
        """Ricalcola % completamento dai AuditPrep reali."""
        from .services import sync_program_completion
        program = self.get_object()
        pct = sync_program_completion(program)
        return Response({"ok": True, "completion_pct": pct, "status": program.status})

    @action(detail=True, methods=["get"], url_path="report")
    def report(self, request, pk=None):
        """Relazione HTML del programma annuale."""
        import html as _html

        from django.http import HttpResponse
        program = self.get_object()
        preps = AuditPrep.objects.filter(
            audit_program=program
        ).prefetch_related("evidence_items", "findings")

        def _e(value) -> str:
            # Gli audit pianificati (titolo, auditor, framework) sono input utente
            # liberi salvati nel JSON `planned_audits`: vanno escapati prima di
            # finire nell'HTML del report scaricabile (no XSS-on-open).
            return _html.escape(str(value)) if value is not None else "—"

        rows = ""
        for audit in program.planned_audits:
            prep_id = audit.get("audit_prep_id")
            prep = preps.filter(pk=prep_id).first() if prep_id else None
            score = prep.readiness_score if prep else None
            status = audit.get("status", "planned")
            status_colors = {
                "planned": "#6b7280", "in_progress": "#2563eb",
                "completed": "#16a34a", "cancelled": "#dc2626",
            }
            color = status_colors.get(status, "#6b7280")
            rows += (
                f"<tr><td>Q{_e(audit.get('quarter', '—'))}</td>"
                f"<td>{_e(audit.get('title', '—'))}</td>"
                f"<td>{_e(', '.join(audit.get('framework_codes', [])))}</td>"
                f"<td>{_e(audit.get('planned_date', '—'))}</td>"
                f"<td>{_e(audit.get('auditor_name', '—'))}</td>"
                f"<td style='color:{color};font-weight:bold'>{_e(status.replace('_', ' ').title())}</td>"
                f"<td style='font-weight:bold'>{f'{score}/100' if score is not None else '—'}</td></tr>"
            )

        from django.utils import timezone as tz
        html = f"""<!DOCTYPE html>
<html lang="it"><head><meta charset="UTF-8">
<title>Programma Audit {_e(program.year)}</title>
<style>
body{{font-family:Arial,sans-serif;font-size:10px;margin:24px}}
h1{{font-size:16px;color:#1e40af;border-bottom:2px solid #1e40af;padding-bottom:6px}}
table{{width:100%;border-collapse:collapse;margin:12px 0}}
th{{background:#1e40af;color:white;padding:5px 6px;text-align:left}}
td{{padding:4px 6px;border-bottom:1px solid #e5e7eb}}
tr:nth-child(even){{background:#f9fafb}}
</style></head><body>
<h1>Programma Audit Annuale {_e(program.year)}</h1>
<p><strong>Sito:</strong> {_e(program.plant.name)} &nbsp;
   <strong>Stato:</strong> {_e(program.status)} &nbsp;
   <strong>Completamento:</strong> {program.completion_pct}%</p>
<table>
<tr><th>Q</th><th>Titolo</th><th>Framework</th><th>Data</th><th>Auditor</th><th>Stato</th><th>Score</th></tr>
{rows}
</table></body></html>"""

        filename = f"ProgrammaAudit_{program.year}_{tz.now().strftime('%Y%m%d')}.html"
        resp = HttpResponse(html, content_type="text/html; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp

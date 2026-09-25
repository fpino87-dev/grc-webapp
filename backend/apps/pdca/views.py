import uuid

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.audit import log_action
from core.scoping import PlantScopedQuerysetMixin, require_org_scope_for_org_wide, user_has_org_scope

from . import services
from .models import PdcaCycle, PdcaPhase
from .permissions import PdcaPermission
from .serializers import PdcaCycleSerializer, PdcaPhaseSerializer


class PdcaCycleViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = PdcaCycle.objects.select_related("plant", "archive_evidence").prefetch_related(
        "phases", "findings__audit_prep__plant", "findings__audit_prep__group",
    )
    serializer_class = PdcaCycleSerializer
    permission_classes = [PdcaPermission]
    # trigger_type si filtra per categoria in get_queryset (TRIGGER_GROUPS)
    filterset_fields = ["id", "plant", "fase_corrente"]
    # ?search= testo libero: ciclo, riferimento e finding/audit collegati
    search_fields = [
        "title", "descrizione", "riferimento_finding",
        "findings__title", "findings__audit_prep__title",
    ]
    plant_field = "plant"
    # I cicli di organizzazione (plant=None) sono visibili a tutti i siti.
    allow_null_plant = True

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        # ?open=true → solo cicli ancora aperti (collegabili a un finding).
        if params.get("open", "").lower() == "true":
            qs = qs.exclude(fase_corrente__in=["chiuso", "archiviato"])
        # ?trigger_type=<categoria> → tutti i codici della categoria (es. audit
        # comprende i PDCA aperti dai finding); un codice esatto resta valido.
        trigger = params.get("trigger_type")
        if trigger:
            qs = qs.filter(trigger_type__in=services.TRIGGER_GROUPS.get(trigger, [trigger]))
        # ?org=true → solo i cicli di organizzazione.
        if params.get("org", "").lower() == "true":
            qs = qs.filter(plant__isnull=True)
        # ?site=<id> → cicli del sito + cicli di organizzazione (valgono anche
        # per quel sito). `?plant=<id>` resta il filtro esatto sul sito.
        site = params.get("site")
        if site:
            try:
                site = uuid.UUID(str(site))
            except ValueError:
                return qs.none()
            qs = qs.filter(Q(plant_id=site) | Q(plant__isnull=True))
        return qs

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["can_manage_org"] = user_has_org_scope(self.request.user)
        return ctx

    @action(detail=False, methods=["get"], url_path="capabilities")
    def capabilities(self, request):
        """GET /pdca/cycles/capabilities/ — l'utente può aprire e gestire cicli
        di organizzazione? (il backend ricontrolla ogni scrittura)."""
        return Response({"can_manage_org": user_has_org_scope(request.user)})

    def _scoped_finding(self, finding_id):
        """Finding visibile all'utente (perimetro del sito dell'audit), o 404."""
        from rest_framework.exceptions import NotFound

        from apps.audit_prep.models import AuditFinding
        from core.scoping import scope_queryset_by_plant

        try:
            pk = uuid.UUID(str(finding_id))
        except (TypeError, ValueError):
            raise NotFound(_("Finding non trovato.")) from None
        finding = scope_queryset_by_plant(
            AuditFinding.objects.select_related("audit_prep"), self.request.user,
            plant_field="audit_prep__plant",
        ).filter(pk=pk).first()
        if finding is None:
            raise NotFound(_("Finding non trovato."))
        return finding

    def perform_create(self, serializer):
        from rest_framework.exceptions import ValidationError as DRFValidationError

        from apps.audit_prep import services as audit_services

        # Nuovo ciclo nato da un finding di audit: sito, trigger e tipo di audit
        # vengono dal finding (non dal form), poi il collegamento univoco.
        finding_id = self.request.data.get("finding")
        if finding_id:
            finding = self._scoped_finding(finding_id)
            if finding.pdca_cycle_id:
                raise DRFValidationError({"error": _("Il finding è già collegato a un PDCA.")})
            cycle = serializer.save(
                created_by=self.request.user,
                plant=finding.audit_prep.plant,
                trigger_type=audit_services.PDCA_TRIGGER_MAP[finding.finding_type],
                trigger_source_id=finding.pk,
                scope_type="finding",
                scope_id=finding.pk,
                audit_subtype=finding.audit_prep.audit_type,
            )
            for fase in services.PHASE_ORDER:
                PdcaPhase.objects.get_or_create(cycle=cycle, phase=fase)
            try:
                audit_services.link_finding_to_pdca(finding, cycle, self.request.user)
            except ValidationError as exc:
                raise DRFValidationError({"error": exc.messages[0]}) from exc
            log_action(
                user=self.request.user, action_code="pdca.cycle.create", level="L2", entity=cycle,
                payload={"cycle_id": str(cycle.pk), "title": cycle.title, "finding": str(finding.pk)},
            )
            return

        plant = serializer.validated_data.get("plant")
        require_org_scope_for_org_wide(self.request.user, plant)
        extra = {"scope_type": "org"} if plant is None else {}
        cycle = serializer.save(created_by=self.request.user, **extra)
        # Create the four PDCA phase records for this cycle
        for fase in services.PHASE_ORDER:
            PdcaPhase.objects.get_or_create(cycle=cycle, phase=fase)
        log_action(
            user=self.request.user,
            action_code="pdca.cycle.create",
            level="L2",
            entity=cycle,
            payload={"cycle_id": str(cycle.pk), "title": cycle.title},
        )

    def perform_update(self, serializer):
        # Un ciclo di sito non diventa di organizzazione senza scope org
        # (quello già di organizzazione è coperto da PdcaPermission).
        if "plant" in serializer.validated_data:
            require_org_scope_for_org_wide(self.request.user, serializer.validated_data["plant"])
        cycle = serializer.save()
        log_action(
            user=self.request.user,
            action_code="pdca.cycle.updated",
            level="L2",
            entity=cycle,
            payload={
                "cycle_id": str(cycle.pk),
                "updated_fields": list(serializer.validated_data.keys()),
            },
        )

    @action(detail=True, methods=["post"], url_path="link-finding")
    def link_finding(self, request, pk=None):
        """POST /pdca/cycles/<id>/link-finding/ {finding, reason?} → collega un finding
        di audit (stesso sito; più finding solo dello stesso audit). Se il finding
        ha già un PDCA lo sostituisce (`reason` obbligatorio)."""
        from apps.audit_prep import services as audit_services

        cycle = self.get_object()
        finding = self._scoped_finding(request.data.get("finding"))
        try:
            with transaction.atomic():
                # ciclo di organizzazione: il rilievo comune su tutti i siti
                if cycle.plant_id is None:
                    audit_services.link_common_findings_to_pdca(
                        finding, cycle, request.user, request.data.get("reason", ""),
                    )
                # finding con già un PDCA (es. quello automatico della NC):
                # sostituzione, con motivo obbligatorio
                elif finding.pdca_cycle_id:
                    audit_services.replace_finding_pdca(
                        finding, cycle, request.user, request.data.get("reason", ""),
                    )
                else:
                    audit_services.link_finding_to_pdca(finding, cycle, request.user)
        except ValidationError as exc:
            return Response({"error": exc.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        cycle = self.get_queryset().get(pk=cycle.pk)
        return Response(self.get_serializer(cycle).data)

    @action(detail=True, methods=["post"], url_path="unlink-finding")
    def unlink_finding(self, request, pk=None):
        """POST /pdca/cycles/<id>/unlink-finding/ {finding, reason}."""
        from apps.audit_prep import services as audit_services

        cycle = self.get_object()
        finding = self._scoped_finding(request.data.get("finding"))
        if finding.pdca_cycle_id != cycle.pk:
            return Response({"error": _("Il finding non è collegato a questo PDCA.")},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            audit_services.unlink_finding_from_pdca(finding, request.user, request.data.get("reason", ""))
        except ValidationError as exc:
            return Response({"error": exc.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        cycle = self.get_queryset().get(pk=cycle.pk)
        return Response(self.get_serializer(cycle).data)

    @action(detail=True, methods=["post"], url_path="advance")
    def advance(self, request, pk=None):
        from apps.documents.models import Evidence

        cycle = self.get_object()
        notes = request.data.get("notes", "")
        outcome = request.data.get("outcome", "")
        evidence_id = request.data.get("evidence_id")
        # In DO si può scegliere un'evidenza esistente oppure caricare il file
        # (multipart `file` + `evidence_title` opzionale) nella stessa richiesta.
        uploaded_file = request.FILES.get("file")
        if uploaded_file and evidence_id:
            return Response(
                {"error": _("Carica un file oppure scegli un'evidenza esistente, non entrambi.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if uploaded_file and cycle.fase_corrente != "do":
            return Response(
                {"error": _("Il file dell'evidenza si carica solo nel passaggio da DO a CHECK.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        evidence = None
        if evidence_id:
            evidence = Evidence.objects.filter(pk=evidence_id).first()
            if not evidence:
                return Response({"error": _("Evidenza non trovata")}, status=status.HTTP_404_NOT_FOUND)
        try:
            with transaction.atomic():
                if uploaded_file:
                    evidence = services.create_cycle_evidence(
                        cycle, uploaded_file, request.user, title=request.data.get("evidence_title", ""),
                    )
                cycle = services.advance_phase(
                    cycle,
                    request.user,
                    phase_notes=notes,
                    evidence=evidence,
                    outcome=outcome,
                )
            return Response(
                {
                    "ok": True,
                    "fase_corrente": cycle.fase_corrente,
                    "reopened_as": str(cycle.reopened_as.pk) if cycle.reopened_as else None,
                    "evidence_id": str(evidence.pk) if evidence else None,
                }
            )
        except ValidationError as exc:
            return Response({"error": exc.messages[0] if exc.messages else str(exc)},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request, pk=None):
        cycle = self.get_object()
        act_description = request.data.get("act_description", "")
        try:
            cycle = services.close_cycle(cycle, request.user, act_description)
            return Response({"ok": True, "fase_corrente": "chiuso"})
        except ValidationError as exc:
            return Response({"error": str(exc.message)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="archivia")
    def archivia(self, request, pk=None):
        """POST {motivo, evidence_id?} o multipart con `file` (+ `evidence_title`).
        Le osservazioni/opportunità collegate aperte diventano "non perseguite"."""
        from apps.audit_prep.views import _require_all_group_sites
        from apps.documents.models import Evidence
        from core.scoping import scope_queryset_by_plant

        cycle = self.get_object()
        # rilievo comune: la decisione tocca anche gli altri siti del gruppo
        for f in cycle.findings.filter(common_key__isnull=False).select_related("audit_prep__group"):
            if f.audit_prep.group_id:
                _require_all_group_sites(request.user, f.audit_prep.group)
        evidence = None
        evidence_id = request.data.get("evidence_id")
        if evidence_id:
            try:
                evidence = scope_queryset_by_plant(
                    Evidence.objects.all(), request.user, plant_field="plant",
                ).filter(pk=uuid.UUID(str(evidence_id))).first()
            except ValueError:
                evidence = None
            if evidence is None:
                return Response({"error": _("Evidenza non trovata.")}, status=status.HTTP_404_NOT_FOUND)
        try:
            result = services.archivia_with_findings(
                cycle, request.user, request.data.get("motivo", ""), evidence=evidence,
                uploaded_file=request.FILES.get("file"), evidence_title=request.data.get("evidence_title", ""),
            )
        except ValidationError as exc:
            return Response({"error": exc.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"ok": True, "fase_corrente": "archiviato", **result})

    def destroy(self, request, *args, **kwargs):
        """Soft-delete del ciclo PDCA con vincoli a tutela dell'audit trail.

        Bloccato se:
          - il ciclo e' gia' chiuso (la Lesson Learned generata dipende dal
            cycle.pk e l'auditor si aspetta una traccia coerente);
          - esistono `AuditFinding` aperti **manuali** (`auto_generated=False`)
            che referenziano il ciclo: il finding senza PDCA tracciante
            perderebbe la sua azione correttiva.

        Cancellazione cooperativa:
          - le `PdcaPhase` figlie vengono soft-deleted in cascata;
          - i finding `auto_generated=True` ancora aperti (creati dalla
            auto-validation insieme al ciclo) vengono soft-deleted insieme:
            sono parte della stessa catena automatica e non hanno senso senza
            il ciclo che li tracciava.
          - Eventuali `AuditFinding` chiusi mantengono il FK (con
            `on_delete=SET_NULL` sul modello) — il SoftDeleteManager filtrera'
            fuori il PDCA, quindi la query cycle.findings non lo restituira'
            piu'.
        """
        from apps.audit_prep.models import AuditFinding

        cycle = self.get_object()
        reason = (request.data.get("reason") or "").strip()
        if len(reason) < 10:
            return Response(
                {"error": _("Motivo cancellazione obbligatorio (min 10 caratteri).")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if cycle.fase_corrente == "chiuso":
            return Response(
                {"error": _(
                    "Ciclo gia' chiuso: ha generato una Lesson Learned e fa "
                    "parte dell'audit trail. Non e' cancellabile."
                )},
                status=status.HTTP_400_BAD_REQUEST,
            )

        open_findings_qs = AuditFinding.objects.filter(
            pdca_cycle=cycle,
            status__in=["open", "in_response"],
            deleted_at__isnull=True,
        )
        manual_open = open_findings_qs.filter(auto_generated=False).count()
        if manual_open > 0:
            return Response(
                {"error": _(
                    "Impossibile cancellare: %(count)d finding manuali aperti "
                    "referenziano questo ciclo. Chiudi o annulla prima i finding."
                ) % {"count": manual_open}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            now = timezone.now()
            cascaded_findings = list(
                open_findings_qs.filter(auto_generated=True)
            )
            for finding in cascaded_findings:
                finding.soft_delete()
            PdcaPhase.objects.filter(
                cycle=cycle, deleted_at__isnull=True,
            ).update(deleted_at=now, updated_at=now)
            cycle.soft_delete()
            log_action(
                user=request.user,
                action_code="pdca.cycle.deleted",
                level="L2",
                entity=cycle,
                payload={
                    "cycle_id": str(cycle.pk),
                    "title": cycle.title,
                    "fase_corrente_at_delete": cycle.fase_corrente,
                    "trigger_type": cycle.trigger_type,
                    "reason": reason[:200],
                    "auto_findings_cascaded": [str(f.pk) for f in cascaded_findings],
                },
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class PdcaPhaseViewSet(
    PlantScopedQuerysetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Sola lettura — le fasi sono interamente gestite dal workflow
    (`create_cycle` / `advance_phase`). Esporre create/update/destroy darebbe
    accesso a hard-delete senza audit e a duplicazione/manomissione dei record
    di fase, scavalcando il ciclo PDCA. Nessun client le scrive direttamente."""

    queryset = PdcaPhase.objects.select_related("cycle")
    serializer_class = PdcaPhaseSerializer
    permission_classes = [PdcaPermission]
    filterset_fields = ["cycle", "phase"]
    plant_field = "cycle__plant"
    allow_null_plant = True

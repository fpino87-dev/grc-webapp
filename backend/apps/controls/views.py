from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from .models import Control, ControlDomain, ControlInstance, Framework
from .serializers import (
    ControlDomainSerializer,
    ControlInstanceSerializer,
    ControlSerializer,
    FrameworkSerializer,
)


class FrameworkViewSet(viewsets.ModelViewSet):
    serializer_class   = FrameworkSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        plant_id = self.request.query_params.get("plant")
        if plant_id:
            from apps.plants.services import get_active_frameworks
            from apps.plants.models import Plant
            plant = Plant.objects.filter(pk=plant_id).first()
            if plant:
                return get_active_frameworks(plant)
        return Framework.objects.filter(archived_at__isnull=True)

    def destroy(self, request, *args, **kwargs):
        from django.core.exceptions import ValidationError

        from .services import archive_framework

        fw = self.get_object()
        try:
            archive_framework(fw, request.user)
        except ValidationError as e:
            return Response(
                {"detail": e.messages[0] if getattr(e, "messages", None) else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["delete"], url_path="delete")
    def delete_framework(self, request, pk=None):
        from django.core.exceptions import ValidationError

        from .services import delete_framework

        fw = self.get_object()
        try:
            delete_framework(fw, request.user)
        except ValidationError as e:
            return Response(
                {"detail": e.messages[0] if getattr(e, "messages", None) else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="governance")
    def governance_list(self, request):
        """
        Governance list: framework metadata + counts + available languages.
        """
        from .services import list_framework_governance_metadata
        return Response({"results": list_framework_governance_metadata()})

    @action(
        detail=False,
        methods=["post"],
        url_path="import-preview",
    )
    def import_preview(self, request):
        """
        Preview import (validate + summary). Expects JSON body.
        """
        from django.utils.translation import gettext as _
        from django.core.exceptions import ValidationError
        from .services import preview_framework_import

        if not request.user.is_superuser:
            return Response({"error": _("Solo il superuser può importare framework.")}, status=403)
        try:
            return Response(preview_framework_import(request.data))
        except ValidationError as e:
            return Response({"error": str(e.message)}, status=400)

    @action(
        detail=False,
        methods=["post"],
        url_path="import",
    )
    def import_framework(self, request):
        """
        Import framework JSON. Expects JSON body with optional 'sha256' for confirmation.
        """
        from django.utils.translation import gettext as _
        from django.core.exceptions import ValidationError
        from .services import preview_framework_import, import_framework_payload

        if not request.user.is_superuser:
            return Response({"error": _("Solo il superuser può importare framework.")}, status=403)

        # If client sends sha256, verify matches preview for the provided payload
        client_sha = request.data.get("sha256")
        payload = dict(request.data)
        payload.pop("sha256", None)
        try:
            preview = preview_framework_import(payload)
            if client_sha and client_sha != preview.get("sha256"):
                return Response({"error": _("Conferma import non valida (sha256 mismatch).")}, status=400)
            return Response(import_framework_payload(payload, request.user))
        except ValidationError as e:
            return Response({"error": str(e.message)}, status=400)


class ControlDomainViewSet(viewsets.ModelViewSet):
    queryset = ControlDomain.objects.select_related("framework")
    serializer_class = ControlDomainSerializer


class ControlViewSet(viewsets.ModelViewSet):
    queryset = Control.objects.select_related("framework", "domain")
    serializer_class = ControlSerializer

    @action(detail=True, methods=["post"], url_path="explain")
    def explain(self, request, pk=None):
        """
        Genera (o rigenera) la spiegazione plain-language del controllo via AI.
        Body: { "lang": "it" }
        """
        from apps.ai_engine.tasks_ai import explain_control
        from django.utils.translation import gettext as _

        control = self.get_object()
        lang = request.data.get("lang", "it")
        try:
            result = explain_control(control, lang, request.user)
            return Response(result)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"explain_control error: {e}")
            return Response({"error": _("Generazione spiegazione non riuscita: %(err)s") % {"err": str(e)}}, status=500)

    @action(detail=True, methods=["post"], url_path="generate-document")
    def generate_document(self, request, pk=None):
        """
        Genera un documento .docx di procedura operativa per il controllo via AI.
        Body: { "lang": "it" }
        """
        import logging
        from django.http import HttpResponse
        from django.utils.translation import gettext as _
        from core.audit import log_action
        from .services import generate_procedure_document

        control = self.get_object()
        lang = request.data.get("lang", "it")
        try:
            docx_bytes = generate_procedure_document(control, lang, request.user)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        except Exception as e:
            logging.getLogger(__name__).error(f"generate_document error [{control.external_id}]: {e}")
            return Response(
                {"error": _("Generazione documento non riuscita: %(err)s") % {"err": str(e)}},
                status=500,
            )

        log_action(
            user=request.user,
            action_code="control.document_generated",
            level="L1",
            entity=control,
            payload={"lang": lang},
        )

        filename = f"{control.external_id}_procedura.docx"
        response = HttpResponse(
            docx_bytes,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


def _explain_suggestion(instance) -> str:
    from .services import calc_suggested_status, check_evidence_requirements
    from django.utils.translation import gettext as _

    req = instance.control.evidence_requirement or {}
    has_req = bool(
        req.get("documents") or req.get("evidences")
        or req.get("min_documents") or req.get("min_evidences")
    )
    if not has_req:
        return _("Nessun requisito documentale definito per questo controllo.")

    suggested = calc_suggested_status(instance)
    if suggested == "compliant":
        return _("Tutti i requisiti documentali sono soddisfatti.")

    check = check_evidence_requirements(instance)
    msgs = []
    for md in check["missing_documents"]:
        msgs.append(_("Documento mancante: %(desc)s") % {"desc": md["description"] or md["type"]})
    for me in check["missing_evidences"]:
        msgs.append(_("Evidenza mancante: %(desc)s") % {"desc": me["description"] or me["type"]})
    for ee in check["expired_evidences"]:
        msgs.append(
            _("Evidenza scaduta: %(title)s (scaduta il %(date)s)") % {
                "title": ee["title"],
                "date": ee["expired_on"],
            }
        )

    prefix = _("Requisiti parzialmente soddisfatti.") if suggested == "parziale" else _("Nessuna documentazione presente.")
    return (prefix + " " + "; ".join(msgs)) if msgs else prefix


class ControlInstanceViewSet(viewsets.ModelViewSet):
    queryset = ControlInstance.objects.select_related(
        "plant", "control__framework", "control__domain", "owner"
    ).prefetch_related(
        "control__mappings_from__target_control__framework",
        "control__mappings_to__source_control__framework",
        "documents",
        "evidences",
    ).order_by("control__framework__code", "control__external_id")
    serializer_class = ControlInstanceSerializer

    def destroy(self, request, *args, **kwargs):
        from django.core.exceptions import ValidationError

        from .services import delete_control_instance

        instance = self.get_object()
        try:
            delete_control_instance(instance, request.user)
        except ValidationError as e:
            return Response(
                {"detail": e.messages[0] if getattr(e, "messages", None) else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        qs        = super().get_queryset()
        plant_id  = self.request.query_params.get("plant")
        status    = self.request.query_params.get("status")
        framework = self.request.query_params.get("framework")

        if plant_id:
            qs = qs.filter(plant_id=plant_id)
            if not framework:
                from apps.plants.services import get_active_frameworks
                from apps.plants.models import Plant
                plant = Plant.objects.filter(pk=plant_id).first()
                if plant:
                    qs = qs.filter(control__framework__in=get_active_frameworks(plant))
                # Deduplication VH/base: se il plant ha sia il controllo base (L2)
                # che il corrispondente VH (L3) collegati da 'extends', mostra solo
                # la versione più specifica (VH) — valutare entrambi è ridondante.
                from .models import ControlMapping
                plant_fw_ids = qs.values_list(
                    "control__framework_id", flat=True
                ).distinct()
                superseded_ids = ControlMapping.objects.filter(
                    relationship="extends",
                    source_control__framework_id__in=plant_fw_ids,
                    target_control__framework_id__in=plant_fw_ids,
                ).values_list("target_control_id", flat=True)
                if superseded_ids.exists():
                    qs = qs.exclude(control_id__in=superseded_ids)
        else:
            # Without plant filter, only return instances whose framework is actually
            # assigned to the plant (prevents showing orphaned instances as duplicates)
            from apps.plants.models import PlantFramework
            from django.db.models import OuterRef, Exists
            assigned = PlantFramework.objects.filter(
                plant=OuterRef("plant"),
                framework=OuterRef("control__framework"),
                deleted_at__isnull=True,
            )
            qs = qs.filter(Exists(assigned))
        if status:
            qs = qs.filter(status=status)
        if framework:
            qs = qs.filter(control__framework__code=framework)
        return qs

    @action(detail=True, methods=["post"])
    def propagate(self, request, pk=None):
        """
        Propaga lo stato ai controlli mappati rispettando tipo di relazione e direzione.
        Body opzionale: { "cross_plant": true }
        """
        from .services import propagate_control
        instance = self.get_object()
        cross_plant = bool(request.data.get("cross_plant", False))
        result = propagate_control(instance, request.user, cross_plant=cross_plant)
        return Response(result)

    @action(detail=True, methods=["post"], url_path="evaluate")
    def evaluate(self, request, pk=None):
        """
        Body: { "status": "compliant", "note": "..." }
        Chiama services.evaluate_control() — lancia 400 se mancano evidenze valide.
        """
        from .services import evaluate_control
        from django.core.exceptions import ValidationError

        instance = self.get_object()
        new_status = request.data.get("status")
        note = request.data.get("note", "")
        if not new_status:
            from django.utils.translation import gettext as _
            return Response({"error": _("Campo 'status' obbligatorio.")}, status=400)
        try:
            evaluate_control(instance, new_status, request.user, note)
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except ValidationError as e:
            return Response({"error": e.message}, status=400)

    @action(detail=True, methods=["get"], url_path="detail-info")
    def detail_info(self, request, pk=None):
        """
        Restituisce info complete per il drawer:
        descrizione, framework mappati, evidenze, storico valutazioni.
        """
        from django.utils import timezone
        from core.audit import AuditLog

        from django.utils import translation

        instance = self.get_object()
        lang = request.query_params.get("lang") or getattr(request, "LANGUAGE_CODE", None) or "it"
        control = instance.control

        mappings = list(
            control.mappings_from.select_related("target_control__framework").values(
                "target_control__framework__code",
                "target_control__external_id",
                "relationship",
            )
        )

        history = list(
            AuditLog.objects.filter(
                entity_type="controlinstance",
                entity_id=instance.pk,
                action_code="control.evaluated",
            )
            .order_by("-timestamp_utc")[:10]
            .values("timestamp_utc", "user_email_at_time", "payload")
        )

        today = timezone.now().date()
        current_evidences = [
            {
                "id": str(e.id),
                "title": e.title,
                "valid_until": str(e.valid_until) if e.valid_until else None,
                "expired": bool(e.valid_until and e.valid_until < today),
                "evidence_type": e.evidence_type,
            }
            for e in instance.evidences.all()
        ]

        linked_documents = [
            {
                "id": str(d.id),
                "title": d.title,
                "document_type": d.document_type,
                "status": d.status,
                "review_due_date": str(d.review_due_date) if d.review_due_date else None,
            }
            for d in instance.documents.filter(deleted_at__isnull=True)
        ]

        from .services import check_evidence_requirements
        with translation.override(lang):
            requirements = check_evidence_requirements(instance, lang=lang)

        from .services import calc_suggested_status
        suggested_status = calc_suggested_status(instance)

        with translation.override(lang):
            return Response({
                "current_status": instance.status,
                "suggested_status": suggested_status,
                "suggested_status_reason": _explain_suggestion(instance),
                "applicability": instance.applicability,
                "exclusion_justification": instance.exclusion_justification,
                "na_justification": instance.na_justification,
                "maturity_level": instance.maturity_level,
                "maturity_level_override": instance.maturity_level_override,
                "calc_maturity_level": instance.calc_maturity_level,
                "approved_in_soa": instance.approved_in_soa,
                "soa_approved_at": instance.soa_approved_at.isoformat() if instance.soa_approved_at else None,
                "needs_revaluation": instance.needs_revaluation,
                "needs_revaluation_since": str(instance.needs_revaluation_since) if instance.needs_revaluation_since else None,
                "notes": instance.notes,
                "control_id": control.external_id,
                "control_uuid": str(control.pk),
                "title": control.get_title(lang),
                "domain": control.domain.get_name(lang) if control.domain else "",
                "framework": control.framework.code,
                "level": control.level,
                "control_category": control.control_category,
                "evidence_requirement": control.evidence_requirement,
                "description": control.translations.get(lang, {}).get("description", ""),
                "practical_summary": control.translations.get(lang, {}).get("practical_summary", ""),
                "implementation_guidance": control.translations.get(lang, {}).get("guidance", ""),
                "evidence_examples": control.translations.get(lang, {}).get("evidence_examples", []),
                "mappings": mappings,
                "evaluation_history": history,
                "current_evidences": current_evidences,
                "linked_documents": linked_documents,
                "requirements": requirements,
            })

    @action(detail=True, methods=["post"], url_path="link-document")
    def link_document(self, request, pk=None):
        """Collega un Document a questo ControlInstance."""
        from apps.documents.models import Document
        from django.utils.translation import gettext as _
        instance = self.get_object()
        doc_id = request.data.get("document_id")
        try:
            doc = Document.objects.get(pk=doc_id, deleted_at__isnull=True)
            instance.documents.add(doc)
            return Response({"ok": True, "document_id": str(doc.id)})
        except Document.DoesNotExist:
            return Response({"error": _("Documento non trovato")}, status=404)

    @action(detail=True, methods=["post"], url_path="unlink-document")
    def unlink_document(self, request, pk=None):
        """Scollega un Document da questo ControlInstance."""
        from apps.documents.models import Document
        from django.utils.translation import gettext as _
        instance = self.get_object()
        doc_id = request.data.get("document_id")
        try:
            doc = Document.objects.get(pk=doc_id)
            instance.documents.remove(doc)
            return Response({"ok": True})
        except Document.DoesNotExist:
            return Response({"error": _("Documento non trovato")}, status=404)

    @action(detail=True, methods=["post"], url_path="link_evidence")
    def link_evidence(self, request, pk=None):
        from apps.documents.models import Evidence
        from django.utils.translation import gettext as _
        instance = self.get_object()
        evidence_id = request.data.get("evidence_id")
        try:
            evidence = Evidence.objects.get(pk=evidence_id)
        except Evidence.DoesNotExist:
            return Response({"error": _("Evidenza non trovata.")}, status=404)
        instance.evidences.add(evidence)
        return Response({"ok": True})

    @action(detail=True, methods=["post"], url_path="set-applicability")
    def set_applicability(self, request, pk=None):
        from .services import validate_exclusion
        from django.core.exceptions import ValidationError
        instance = self.get_object()
        applicability = request.data.get("applicability", "applicabile")
        justification = request.data.get("justification", "")
        try:
            validate_exclusion(instance, applicability, justification, request.user)
            return Response({"ok": True, "applicability": applicability})
        except ValidationError as e:
            return Response({"error": str(e.message)}, status=400)

    @action(detail=True, methods=["post"], url_path="set-maturity")
    def set_maturity(self, request, pk=None):
        """Override manuale del maturity level per VDA ISA TISAX."""
        from core.audit import log_action
        from django.utils.translation import gettext as _
        instance = self.get_object()
        level = request.data.get("maturity_level")
        if level is None or not (0 <= int(level) <= 5):
            return Response({"error": _("maturity_level deve essere tra 0 e 5")}, status=400)
        instance.maturity_level = int(level)
        instance.maturity_level_override = True
        instance.save(update_fields=["maturity_level", "maturity_level_override", "updated_at"])
        log_action(
            user=request.user,
            action_code="control.maturity_override",
            level="L2",
            entity=instance,
            payload={"maturity_level": int(level)},
        )
        return Response({"ok": True, "maturity_level": int(level)})

    @action(detail=False, methods=["post"], url_path="bulk-approve-soa")
    def bulk_approve_soa(self, request):
        """Approva formalmente un gruppo di ControlInstance per il SOA."""
        from django.utils import timezone
        from core.audit import log_action
        ids = request.data.get("instance_ids", [])
        qs = self.get_queryset().filter(pk__in=ids)
        now = timezone.now()
        qs.update(
            approved_in_soa=True,
            soa_approved_at=now,
            soa_approved_by=request.user,
        )
        for instance in qs:
            log_action(
                user=request.user,
                action_code="control.soa_approved",
                level="L1",
                entity=instance,
                payload={"framework": instance.control.framework.code},
            )
        return Response({"ok": True, "approved_count": qs.count()})

    @action(detail=True, methods=["post"], url_path="apply-suggestion")
    def apply_suggestion(self, request, pk=None):
        """Valuta il controllo applicando lo stato suggerito dal sistema."""
        from .services import calc_suggested_status, evaluate_control
        from django.core.exceptions import ValidationError

        instance = self.get_object()
        suggested = calc_suggested_status(instance)
        note = request.data.get("note", "")
        try:
            evaluate_control(instance, suggested, request.user, note)
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except ValidationError as e:
            return Response({"error": e.message}, status=400)

    @action(detail=True, methods=["post"], url_path="unlink_evidence")
    def unlink_evidence(self, request, pk=None):
        from apps.documents.models import Evidence
        from django.utils.translation import gettext as _
        instance = self.get_object()
        evidence_id = request.data.get("evidence_id")
        try:
            evidence = Evidence.objects.get(pk=evidence_id)
        except Evidence.DoesNotExist:
            return Response({"error": _("Evidenza non trovata.")}, status=404)
        instance.evidences.remove(evidence)
        return Response({"ok": True})

    @action(detail=False, methods=["get"], url_path="needs-revaluation")
    def needs_revaluation_list(self, request):
        """Controlli che richiedono rivalutazione dopo un change."""
        plant_id = request.query_params.get("plant")
        qs = self.get_queryset().filter(needs_revaluation=True)
        if plant_id:
            qs = qs.filter(plant_id=plant_id)
        return Response(self.get_serializer(qs, many=True).data)


class GapAnalysisView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .services import gap_analysis
        from django.utils.translation import gettext as _
        source = request.query_params.get("source")
        target = request.query_params.get("target")
        plant_id = request.query_params.get("plant")
        if not source or not target:
            return Response({"error": _("Parametri 'source' e 'target' obbligatori.")}, status=400)
        lang = request.query_params.get("lang") or getattr(request, "LANGUAGE_CODE", None) or "it"
        result = gap_analysis(source, target, plant_id, lang=lang)
        return Response(result)


class ComplianceExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get_format_suffix(self, **kwargs):
        # DRF usa 'format' come URL_FORMAT_OVERRIDE e lo intercetta dai query params.
        # Il nostro parametro ?format=soa causerebbe Http404 perché non esiste
        # nessun renderer 'soa'. Restituiamo None per disabilitare questa logica.
        return None

    FORMAT_FILENAMES = {
        "soa":               "SOA",
        "vda_isa":           "VDA_ISA",
        "compliance_matrix": "NIS2_Matrix",
    }
    FORMAT_FRAMEWORK = {
        "soa":               ["ISO27001"],
        "vda_isa":           ["TISAX_L2", "TISAX_L3", "TISAX_PROTO"],
        "compliance_matrix": ["NIS2"],
    }

    def get(self, request):
        from .export_engine import generate_export
        from django.http import HttpResponse
        from django.utils import timezone
        from django.utils.translation import gettext as _

        framework_code = request.query_params.get("framework")
        plant_id = request.query_params.get("plant")
        # Usiamo "fmt" invece di "format" per evitare il conflitto con
        # DRF URL_FORMAT_OVERRIDE che intercetta "format" nei query params
        # e tenta di trovare un renderer corrispondente, causando Http404.
        export_format = request.query_params.get("fmt", "soa")

        if not framework_code:
            return Response({"error": _("Parametro 'framework' obbligatorio.")}, status=400)

        allowed = self.FORMAT_FRAMEWORK.get(export_format, [])
        if allowed and framework_code not in allowed:
            return Response({
                "error": _(
                    "Formato %(fmt)s non compatibile con framework %(fw)s. Usa uno di: %(allowed)s"
                ) % {
                    "fmt": export_format,
                    "fw": framework_code,
                    "allowed": ", ".join(allowed),
                }
            }, status=400)

        # Verifica che il framework sia attivo per questo plant
        if plant_id and framework_code:
            from apps.plants.services import get_active_framework_codes
            from apps.plants.models import Plant
            plant = Plant.objects.filter(pk=plant_id).first()
            if plant:
                active_codes = get_active_framework_codes(plant)
                if framework_code not in active_codes:
                    return Response({
                        "error": (
                            _("Framework '%(fw)s' non attivo per questo sito. Framework attivi: %(active)s")
                            % {"fw": framework_code, "active": ", ".join(active_codes)}
                        )
                    }, status=400)

        try:
            html = generate_export(framework_code, plant_id, export_format, request.user)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        except Exception as e:
            import traceback
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Export error [{export_format}/{framework_code}]: {traceback.format_exc()}")
            return Response(
                {"error": _("Errore generazione documento: %(err)s") % {"err": str(e)}},
                status=500,
            )

        from core.audit import log_action
        from apps.plants.models import Plant
        plant = Plant.objects.filter(pk=plant_id).first()
        if plant:
            log_action(
                user=request.user,
                action_code=f"export.{export_format}",
                level="L1",
                entity=plant,
                payload={"framework": framework_code, "format": export_format},
            )

        label = self.FORMAT_FILENAMES.get(export_format, export_format)
        filename = f"{label}_{framework_code}_{timezone.now().strftime('%Y%m%d')}.html"
        response = HttpResponse(html, content_type="text/html; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


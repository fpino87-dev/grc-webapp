from rest_framework import viewsets
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
    queryset = Framework.objects.all()
    serializer_class = FrameworkSerializer


class ControlDomainViewSet(viewsets.ModelViewSet):
    queryset = ControlDomain.objects.select_related("framework")
    serializer_class = ControlDomainSerializer


class ControlViewSet(viewsets.ModelViewSet):
    queryset = Control.objects.select_related("framework", "domain")
    serializer_class = ControlSerializer


def _explain_suggestion(instance) -> str:
    from .services import calc_suggested_status, check_evidence_requirements

    req = instance.control.evidence_requirement or {}
    has_req = bool(
        req.get("documents") or req.get("evidences")
        or req.get("min_documents") or req.get("min_evidences")
    )
    if not has_req:
        return "Nessun requisito documentale definito per questo controllo."

    suggested = calc_suggested_status(instance)
    if suggested == "compliant":
        return "Tutti i requisiti documentali sono soddisfatti."

    check = check_evidence_requirements(instance)
    msgs = []
    for md in check["missing_documents"]:
        msgs.append(f"Documento mancante: {md['description'] or md['type']}")
    for me in check["missing_evidences"]:
        msgs.append(f"Evidenza mancante: {me['description'] or me['type']}")
    for ee in check["expired_evidences"]:
        msgs.append(f"Evidenza scaduta: {ee['title']} (scaduta il {ee['expired_on']})")

    prefix = "Requisiti parzialmente soddisfatti." if suggested == "parziale" else "Nessuna documentazione presente."
    return (prefix + " " + "; ".join(msgs)) if msgs else prefix


class ControlInstanceViewSet(viewsets.ModelViewSet):
    queryset = ControlInstance.objects.select_related(
        "plant", "control__framework", "control__domain"
    ).prefetch_related(
        "control__mappings_from__target_control__framework",
        "control__mappings_to__source_control__framework",
        "documents",
        "evidences",
    )
    serializer_class = ControlInstanceSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        plant_id = self.request.query_params.get("plant")
        status = self.request.query_params.get("status")
        framework = self.request.query_params.get("framework")
        if plant_id:
            qs = qs.filter(plant_id=plant_id)
        if status:
            qs = qs.filter(status=status)
        if framework:
            qs = qs.filter(control__framework__code=framework)
        return qs

    @action(detail=True, methods=["post"])
    def propagate(self, request, pk=None):
        """Copia lo stato di questa istanza a tutti i controlli mappati (stesso sito)."""
        instance = self.get_object()
        target_ids = set()
        for m in instance.control.mappings_from.all():
            target_ids.add(m.target_control_id)
        for m in instance.control.mappings_to.all():
            target_ids.add(m.source_control_id)
        if not target_ids:
            return Response({"propagated_to": 0})
        updated = ControlInstance.objects.filter(
            plant=instance.plant, control_id__in=target_ids
        ).update(status=instance.status)
        return Response({"propagated_to": updated})

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
            return Response({"error": "Campo 'status' obbligatorio."}, status=400)
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

        instance = self.get_object()
        lang = request.query_params.get("lang", "it")
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
                "expired": (e.valid_until < today) if e.valid_until else True,
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
        requirements = check_evidence_requirements(instance)

        from .services import calc_suggested_status
        suggested_status = calc_suggested_status(instance)

        return Response({
            "current_status": instance.status,
            "suggested_status": suggested_status,
            "suggested_status_reason": _explain_suggestion(instance),
            "applicability": instance.applicability,
            "exclusion_justification": instance.exclusion_justification,
            "maturity_level": instance.maturity_level,
            "maturity_level_override": instance.maturity_level_override,
            "calc_maturity_level": instance.calc_maturity_level,
            "approved_in_soa": instance.approved_in_soa,
            "soa_approved_at": instance.soa_approved_at.isoformat() if instance.soa_approved_at else None,
            "needs_revaluation": instance.needs_revaluation,
            "needs_revaluation_since": str(instance.needs_revaluation_since) if instance.needs_revaluation_since else None,
            "control_id": control.external_id,
            "title": control.get_title(lang),
            "domain": control.domain.get_name(lang) if control.domain else "",
            "framework": control.framework.code,
            "level": control.level,
            "control_category": control.control_category,
            "evidence_requirement": control.evidence_requirement,
            "description": control.translations.get(lang, {}).get("description", ""),
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
        instance = self.get_object()
        doc_id = request.data.get("document_id")
        try:
            doc = Document.objects.get(pk=doc_id, deleted_at__isnull=True)
            instance.documents.add(doc)
            return Response({"ok": True, "document_id": str(doc.id)})
        except Document.DoesNotExist:
            return Response({"error": "Documento non trovato"}, status=404)

    @action(detail=True, methods=["post"], url_path="unlink-document")
    def unlink_document(self, request, pk=None):
        """Scollega un Document da questo ControlInstance."""
        from apps.documents.models import Document
        instance = self.get_object()
        doc_id = request.data.get("document_id")
        try:
            doc = Document.objects.get(pk=doc_id)
            instance.documents.remove(doc)
            return Response({"ok": True})
        except Document.DoesNotExist:
            return Response({"error": "Documento non trovato"}, status=404)

    @action(detail=True, methods=["post"], url_path="link_evidence")
    def link_evidence(self, request, pk=None):
        from apps.documents.models import Evidence
        instance = self.get_object()
        evidence_id = request.data.get("evidence_id")
        try:
            evidence = Evidence.objects.get(pk=evidence_id)
        except Evidence.DoesNotExist:
            return Response({"error": "Evidenza non trovata."}, status=404)
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
        instance = self.get_object()
        level = request.data.get("maturity_level")
        if level is None or not (0 <= int(level) <= 5):
            return Response({"error": "maturity_level deve essere tra 0 e 5"}, status=400)
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
        instance = self.get_object()
        evidence_id = request.data.get("evidence_id")
        try:
            evidence = Evidence.objects.get(pk=evidence_id)
        except Evidence.DoesNotExist:
            return Response({"error": "Evidenza non trovata."}, status=404)
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
        source = request.query_params.get("source")
        target = request.query_params.get("target")
        plant_id = request.query_params.get("plant")
        if not source or not target:
            return Response({"error": "Parametri 'source' e 'target' obbligatori."}, status=400)
        result = gap_analysis(source, target, plant_id)
        return Response(result)


class ComplianceExportView(APIView):
    permission_classes = [IsAuthenticated]

    FORMAT_FILENAMES = {
        "soa":               "SOA",
        "vda_isa":           "VDA_ISA",
        "compliance_matrix": "NIS2_Matrix",
    }
    FORMAT_FRAMEWORK = {
        "soa":               ["ISO27001"],
        "vda_isa":           ["TISAX_L2", "TISAX_L3"],
        "compliance_matrix": ["NIS2"],
    }

    def get(self, request):
        from .export_engine import generate_export
        from django.http import HttpResponse
        from django.utils import timezone

        framework_code = request.query_params.get("framework")
        plant_id = request.query_params.get("plant")
        export_format = request.query_params.get("format", "soa")

        if not framework_code:
            return Response({"error": "Parametro framework obbligatorio"}, status=400)

        allowed = self.FORMAT_FRAMEWORK.get(export_format, [])
        if allowed and framework_code not in allowed:
            return Response({
                "error": f"Formato {export_format} non compatibile "
                         f"con framework {framework_code}. "
                         f"Usa uno di: {allowed}"
            }, status=400)

        try:
            html = generate_export(framework_code, plant_id, export_format, request.user)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)

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


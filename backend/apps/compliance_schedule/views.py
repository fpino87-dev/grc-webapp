from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.translation import gettext as _

from core.scoping import PlantScopedQuerysetMixin, require_plant_access

from .models import ComplianceSchedulePolicy, ScheduleRule, RequiredDocument, DEFAULT_RULES, RULE_TYPE_LABELS, RULE_CATEGORIES
from .permissions import CompliancePolicyPermission
from .serializers import (
    ComplianceSchedulePolicySerializer,
    ScheduleRuleSerializer,
    RequiredDocumentSerializer,
)


class ComplianceSchedulePolicyViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ComplianceSchedulePolicy.objects.prefetch_related("rules")
    serializer_class = ComplianceSchedulePolicySerializer
    permission_classes = [CompliancePolicyPermission]
    allow_null_plant = True  # policy globali (plant=null) visibili a tutti

    def get_queryset(self):
        qs = super().get_queryset()
        plant_id = self.request.query_params.get("plant")
        if plant_id:
            qs = qs.filter(plant_id=plant_id)
        return qs

    @action(detail=False, methods=["post"], url_path="create-default")
    def create_default(self, request):
        """Create a policy with all default rules for a plant (or global)."""
        from .services import create_default_policy
        plant_id = request.data.get("plant_id")
        name = request.data.get("name", _("Policy predefinita"))
        # Crea la policy direttamente sul plant richiesto (o globale se assente):
        # serve accesso al sito; policy globale solo a scope org (sweep 2026-06-12).
        require_plant_access(request.user, plant_id or None)
        plant = None
        if plant_id:
            from apps.plants.models import Plant
            try:
                plant = Plant.objects.get(pk=plant_id)
            except Plant.DoesNotExist:
                return Response({"error": _("Plant non trovato")}, status=404)
        policy = create_default_policy(plant=plant, name=name)
        return Response(ComplianceSchedulePolicySerializer(policy).data, status=201)

    @action(detail=True, methods=["patch"], url_path="update-rule")
    def update_rule(self, request, pk=None):
        """Update a single rule within this policy."""
        policy = self.get_object()
        rule_type = request.data.get("rule_type")
        if not rule_type:
            return Response({"error": _("rule_type obbligatorio")}, status=400)
        rule, _created = ScheduleRule.objects.get_or_create(
            policy=policy,
            rule_type=rule_type,
            defaults={
                "frequency_value": DEFAULT_RULES.get(rule_type, (365, "days", 30))[0],
                "frequency_unit": DEFAULT_RULES.get(rule_type, (365, "days", 30))[1],
                "alert_days_before": DEFAULT_RULES.get(rule_type, (365, "days", 30))[2],
            }
        )
        serializer = ScheduleRuleSerializer(rule, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class RequiredDocumentViewSet(viewsets.ModelViewSet):
    """Catalogo documenti obbligatori, editabile da super_admin/compliance_officer
    (scrittura gestita da CompliancePolicyPermission.write_roles). La lettura è
    allargata (dashboard scadenzario)."""

    queryset = RequiredDocument.objects.all()
    serializer_class = RequiredDocumentSerializer
    permission_classes = [CompliancePolicyPermission]

    def get_queryset(self):
        qs = super().get_queryset().order_by("framework", "document_type", "description")
        framework = self.request.query_params.get("framework")
        if framework:
            qs = qs.filter(framework=framework)
        return qs


class ActivityScheduleView(APIView):
    permission_classes = [CompliancePolicyPermission]

    def get(self, request):
        from .services import get_activity_schedule
        plant_id = request.query_params.get("plant")
        # Lo scadenzario è costruito direttamente dal plant richiesto; senza
        # plant aggrega tutti i siti → solo scope org (sweep 2026-06-12).
        require_plant_access(request.user, plant_id or None)
        months_ahead = int(request.query_params.get("months", 6))
        plant = None
        if plant_id:
            from apps.plants.models import Plant
            plant = Plant.objects.filter(pk=plant_id).first()
        activities = get_activity_schedule(plant=plant, months_ahead=months_ahead)
        return Response({"results": activities, "count": len(activities)})


class RequiredDocumentsStatusView(APIView):
    permission_classes = [CompliancePolicyPermission]

    def get(self, request):
        from .services import get_required_documents_status
        plant_id = request.query_params.get("plant")
        require_plant_access(request.user, plant_id or None)
        framework = request.query_params.get("framework", "ISO27001")
        plant = None
        if plant_id:
            from apps.plants.models import Plant
            plant = Plant.objects.filter(pk=plant_id).first()
        result = get_required_documents_status(plant=plant, framework=framework)
        green = sum(1 for r in result if r["traffic_light"] == "green")
        yellow = sum(1 for r in result if r["traffic_light"] == "yellow")
        red = sum(1 for r in result if r["traffic_light"] == "red")
        return Response({
            "framework": framework,
            "total": len(result),
            "green": green,
            "yellow": yellow,
            "red": red,
            "results": result,
        })


class RequiredDocumentLinkablesView(APIView):
    """GET: elementi (Document/Evidence) collegati al controllo del requisito,
    selezionabili per soddisfarlo. Solo ciò che è già linkato al controllo."""

    permission_classes = [CompliancePolicyPermission]

    def get(self, request):
        from .services import get_required_document_linkables

        plant_id = request.query_params.get("plant")
        req_id = request.query_params.get("required_document")
        require_plant_access(request.user, plant_id or None)
        if not plant_id or not req_id:
            return Response({"error": _("plant e required_document obbligatori")}, status=400)
        from apps.plants.models import Plant
        plant = Plant.objects.filter(pk=plant_id).first()
        req = RequiredDocument.objects.filter(pk=req_id).first()
        if plant is None or req is None:
            return Response({"error": _("Requisito o sito non trovato")}, status=404)
        return Response(get_required_document_linkables(req, plant))


class RequiredDocumentFulfillmentView(APIView):
    """POST: collega un Document o una Evidence al requisito per il sito.
    DELETE: rimuove l'aggancio."""

    permission_classes = [CompliancePolicyPermission]

    def post(self, request):
        from django.core.exceptions import ValidationError
        from .services import link_required_document

        plant_id = request.data.get("plant")
        req_id = request.data.get("required_document")
        document_id = request.data.get("document")
        evidence_id = request.data.get("evidence")
        require_plant_access(request.user, plant_id or None)
        if not plant_id or not req_id:
            return Response({"error": _("plant e required_document obbligatori")}, status=400)

        from apps.plants.models import Plant
        from apps.documents.models import Document, Evidence

        plant = Plant.objects.filter(pk=plant_id).first()
        req = RequiredDocument.objects.filter(pk=req_id).first()
        if plant is None or req is None:
            return Response({"error": _("Requisito o sito non trovato")}, status=404)

        document = Document.objects.filter(pk=document_id).first() if document_id else None
        evidence = Evidence.objects.filter(pk=evidence_id).first() if evidence_id else None
        if document_id and document is None:
            return Response({"error": _("Documento non trovato")}, status=404)
        if evidence_id and evidence is None:
            return Response({"error": _("Evidenza non trovata")}, status=404)

        try:
            link_required_document(req, plant, request.user, document=document, evidence=evidence)
        except ValidationError as exc:
            return Response({"error": exc.messages[0] if exc.messages else str(exc)}, status=400)
        return Response({"ok": True}, status=201)

    def delete(self, request):
        from .services import unlink_required_document

        plant_id = request.query_params.get("plant") or request.data.get("plant")
        req_id = request.query_params.get("required_document") or request.data.get("required_document")
        require_plant_access(request.user, plant_id or None)
        if not plant_id or not req_id:
            return Response({"error": _("plant e required_document obbligatori")}, status=400)
        from apps.plants.models import Plant
        plant = Plant.objects.filter(pk=plant_id).first()
        req = RequiredDocument.objects.filter(pk=req_id).first()
        if plant is None or req is None:
            return Response({"error": _("Requisito o sito non trovato")}, status=404)
        unlink_required_document(req, plant)
        return Response(status=204)


class FrameworkControlsView(APIView):
    """Controlli di un framework (external_id + titolo + level) per il picker
    del catalogo documenti obbligatori — così le voci mappano a controlli reali."""

    permission_classes = [CompliancePolicyPermission]

    def get(self, request):
        framework = request.query_params.get("framework")
        if not framework:
            return Response({"results": []})
        from apps.controls.models import Control, Framework

        fw = Framework.objects.filter(code=framework).first()
        if fw is None:
            return Response({"results": []})
        controls = (
            Control.objects.filter(framework=fw, deleted_at__isnull=True)
            .order_by("external_id")
        )
        return Response({
            "results": [
                {"external_id": c.external_id, "title": c.get_title(), "level": c.level or ""}
                for c in controls
            ]
        })


class RuleTypeCatalogueView(APIView):
    permission_classes = [CompliancePolicyPermission]

    def get(self, request):
        return Response({
            "rule_types": [
                {"value": k, "label": v} for k, v in RULE_TYPE_LABELS.items()
            ],
            "categories": RULE_CATEGORIES,
            "defaults": {
                k: {"frequency_value": v[0], "frequency_unit": v[1], "alert_days_before": v[2]}
                for k, v in DEFAULT_RULES.items()
            },
        })

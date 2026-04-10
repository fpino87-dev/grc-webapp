from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.translation import gettext as _

from .models import ComplianceSchedulePolicy, ScheduleRule, RequiredDocument, DEFAULT_RULES, RULE_TYPE_LABELS, RULE_CATEGORIES
from .serializers import (
    ComplianceSchedulePolicySerializer,
    ScheduleRuleSerializer,
    RequiredDocumentSerializer,
)


class ComplianceSchedulePolicyViewSet(viewsets.ModelViewSet):
    queryset = ComplianceSchedulePolicy.objects.prefetch_related("rules")
    serializer_class = ComplianceSchedulePolicySerializer
    permission_classes = [IsAuthenticated]

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
        rule, _ = ScheduleRule.objects.get_or_create(
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


class RequiredDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RequiredDocument.objects.all()
    serializer_class = RequiredDocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        framework = self.request.query_params.get("framework")
        if framework:
            qs = qs.filter(framework=framework)
        return qs


class ActivityScheduleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .services import get_activity_schedule
        plant_id = request.query_params.get("plant")
        months_ahead = int(request.query_params.get("months", 6))
        plant = None
        if plant_id:
            from apps.plants.models import Plant
            plant = Plant.objects.filter(pk=plant_id).first()
        activities = get_activity_schedule(plant=plant, months_ahead=months_ahead)
        return Response({"results": activities, "count": len(activities)})


class RequiredDocumentsStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .services import get_required_documents_status
        plant_id = request.query_params.get("plant")
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


class RuleTypeCatalogueView(APIView):
    permission_classes = [IsAuthenticated]

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

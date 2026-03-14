from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.audit import log_action

from .models import RiskAssessment, RiskDimension, RiskMitigationPlan
from .serializers import RiskAssessmentSerializer, RiskDimensionSerializer, RiskMitigationPlanSerializer


class RiskAssessmentViewSet(viewsets.ModelViewSet):
    queryset = RiskAssessment.objects.select_related("plant", "asset", "assessed_by", "accepted_by")
    serializer_class = RiskAssessmentSerializer
    filterset_fields = ["plant", "status", "assessment_type"]

    def get_queryset(self):
        qs = super().get_queryset()
        risk_level = self.request.query_params.get("risk_level")
        has_pdca = self.request.query_params.get("has_pdca")
        plant = self.request.query_params.get("plant")

        if plant:
            qs = qs.filter(plant_id=plant)

        if risk_level:
            # Filtra per livello calcolato (verde/giallo/rosso)
            if risk_level == "verde":
                qs = qs.filter(score__lte=7)
            elif risk_level == "giallo":
                qs = qs.filter(score__gt=7, score__lte=14)
            elif risk_level == "rosso":
                qs = qs.filter(score__gt=14)

        if has_pdca == "false":
            from apps.pdca.models import PdcaCycle
            ids_with_pdca = PdcaCycle.objects.exclude(
                fase_corrente="chiuso"
            ).values_list("trigger_source_id", flat=True)
            qs = qs.exclude(pk__in=ids_with_pdca)

        return qs

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(
            user=self.request.user,
            action_code="risk.assessment.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "assessment_type": instance.assessment_type},
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(
            user=self.request.user,
            action_code="risk.assessment.update",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "status": instance.status},
        )

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        from django.utils import timezone
        assessment = self.get_object()
        assessment.status = "completato"
        assessment.assessed_by = request.user
        assessment.assessed_at = timezone.now()
        assessment.save(update_fields=["status", "assessed_by", "assessed_at", "updated_at"])
        log_action(
            user=request.user,
            action_code="risk.assessment.complete",
            level="L2",
            entity=assessment,
            payload={"id": str(assessment.id), "status": "completato"},
        )
        serializer = self.get_serializer(assessment)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="accept")
    def accept(self, request, pk=None):
        assessment = self.get_object()
        assessment.risk_accepted = True
        assessment.accepted_by = request.user
        assessment.save(update_fields=["risk_accepted", "accepted_by", "updated_at"])
        log_action(
            user=request.user,
            action_code="risk.assessment.accept",
            level="L3",
            entity=assessment,
            payload={"id": str(assessment.id), "risk_accepted": True},
        )
        serializer = self.get_serializer(assessment)
        return Response(serializer.data)


class RiskDimensionViewSet(viewsets.ModelViewSet):
    queryset = RiskDimension.objects.select_related("assessment")
    serializer_class = RiskDimensionSerializer
    filterset_fields = ["plant"]

    def get_queryset(self):
        qs = super().get_queryset()
        plant = self.request.query_params.get("plant")
        if plant:
            qs = qs.filter(assessment__plant_id=plant)
        return qs

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(
            user=self.request.user,
            action_code="risk.dimension.create",
            level="L1",
            entity=instance,
            payload={"id": str(instance.id), "dimension_code": instance.dimension_code},
        )


class RiskMitigationPlanViewSet(viewsets.ModelViewSet):
    queryset = RiskMitigationPlan.objects.select_related("assessment", "owner", "control_instance")
    serializer_class = RiskMitigationPlanSerializer
    filterset_fields = ["assessment"]

    def get_queryset(self):
        qs = super().get_queryset()
        plant = self.request.query_params.get("plant")
        assessment = self.request.query_params.get("assessment")
        if plant:
            qs = qs.filter(assessment__plant_id=plant)
        if assessment:
            qs = qs.filter(assessment_id=assessment)
        return qs

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(
            user=self.request.user,
            action_code="risk.mitigation_plan.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id)},
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(
            user=self.request.user,
            action_code="risk.mitigation_plan.update",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "completed_at": str(instance.completed_at)},
        )

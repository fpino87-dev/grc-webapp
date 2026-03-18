from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.audit import log_action

from .models import CriticalProcess, RiskDecision, TreatmentOption
from .serializers import CriticalProcessSerializer, RiskDecisionSerializer, TreatmentOptionSerializer
from .services import approve_process, get_process_risk_bcp_snapshot, validate_process


class CriticalProcessViewSet(viewsets.ModelViewSet):
    queryset = CriticalProcess.objects.select_related("plant", "owner", "approved_by", "validated_by")
    serializer_class = CriticalProcessSerializer
    filterset_fields = ["plant", "status"]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(
            user=self.request.user,
            action_code="bia.critical_process.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "name": instance.name},
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(
            user=self.request.user,
            action_code="bia.critical_process.update",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "name": instance.name},
        )

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        process = self.get_object()
        approve_process(process, request.user)
        log_action(
            user=request.user,
            action_code="bia.critical_process.approve",
            level="L3",
            entity=process,
            payload={"id": str(process.id), "name": process.name},
        )
        serializer = self.get_serializer(process)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="validate")
    def validate(self, request, pk=None):
        """
        Transizione da bozza a validato.
        """
        process = self.get_object()
        validate_process(process, request.user)
        log_action(
            user=request.user,
            action_code="bia.critical_process.validate",
            level="L2",
            entity=process,
            payload={"id": str(process.id), "name": process.name},
        )
        serializer = self.get_serializer(process)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="snapshot")
    def snapshot(self, request, pk=None):
        """
        Vista read-only BIA + Risk + BCP per un singolo processo critico.
        Non modifica lo stato, usata solo dalla UI per mostrare la correlazione.
        """
        process = self.get_object()
        data = get_process_risk_bcp_snapshot(process)
        return Response(data)


class TreatmentOptionViewSet(viewsets.ModelViewSet):
    queryset = TreatmentOption.objects.select_related("process")
    serializer_class = TreatmentOptionSerializer
    filterset_fields = ["plant"]

    def get_queryset(self):
        qs = super().get_queryset()
        plant = self.request.query_params.get("plant")
        if plant:
            qs = qs.filter(process__plant_id=plant)
        return qs

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(
            user=self.request.user,
            action_code="bia.treatment_option.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "title": instance.title},
        )


class RiskDecisionViewSet(viewsets.ModelViewSet):
    queryset = RiskDecision.objects.select_related("process", "decided_by", "treatment")
    serializer_class = RiskDecisionSerializer
    filterset_fields = ["plant"]

    def get_queryset(self):
        qs = super().get_queryset()
        plant = self.request.query_params.get("plant")
        if plant:
            qs = qs.filter(process__plant_id=plant)
        return qs

    def perform_create(self, serializer):
        instance = serializer.save(decided_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="bia.risk_decision.create",
            level="L3",
            entity=instance,
            payload={"id": str(instance.id), "decision": instance.decision},
        )

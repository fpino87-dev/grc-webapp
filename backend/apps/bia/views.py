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

    def destroy(self, request, *args, **kwargs):
        """
        Soft delete consentito solo se il processo non ha dipendenze attive.
        Usato per cleanup BIA di prova.
        """
        instance = self.get_object()

        has_risks = instance.risk_assessments.filter(deleted_at__isnull=True).exists()
        has_bcp_fk = instance.bcp_plans.filter(deleted_at__isnull=True).exists()
        from apps.bcp.models import BcpPlan

        has_bcp_m2m = BcpPlan.objects.filter(
            deleted_at__isnull=True,
            critical_processes=instance,
        ).exists()
        has_treatments = instance.treatment_options.filter(deleted_at__isnull=True).exists()
        has_decisions = instance.risk_decisions.filter(deleted_at__isnull=True).exists()
        from apps.assets.models import Asset

        has_assets = Asset.objects.filter(
            deleted_at__isnull=True,
            processes=instance,
        ).exists()

        if any([has_risks, has_bcp_fk, has_bcp_m2m, has_treatments, has_decisions, has_assets]):
            return Response(
                {
                    "detail": "Impossibile eliminare il processo: esistono valutazioni rischio, BCP, opzioni di trattamento, decisioni o asset collegati."
                },
                status=400,
            )

        instance.soft_delete()
        log_action(
            user=request.user,
            action_code="bia.critical_process.deleted",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "name": instance.name},
        )
        return Response(status=204)

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

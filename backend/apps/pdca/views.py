from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.audit import log_action

from .models import PdcaCycle, PdcaPhase
from .serializers import PdcaCycleSerializer, PdcaPhaseSerializer
from . import services


class PdcaCycleViewSet(viewsets.ModelViewSet):
    queryset = PdcaCycle.objects.select_related("plant").prefetch_related("phases")
    serializer_class = PdcaCycleSerializer
    filterset_fields = ["plant", "fase_corrente"]
    search_fields = ["title"]

    def perform_create(self, serializer):
        cycle = serializer.save(created_by=self.request.user)
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

    @action(detail=True, methods=["post"])
    def advance(self, request, pk=None):
        cycle = self.get_object()
        services.advance_phase(cycle, request.user)
        return Response(PdcaCycleSerializer(cycle).data)


class PdcaPhaseViewSet(viewsets.ModelViewSet):
    queryset = PdcaPhase.objects.select_related("cycle")
    serializer_class = PdcaPhaseSerializer
    filterset_fields = ["cycle", "phase"]

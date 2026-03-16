from django.core.exceptions import ValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.audit import log_action

from . import services
from .models import PdcaCycle, PdcaPhase
from .serializers import PdcaCycleSerializer, PdcaPhaseSerializer


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

    @action(detail=True, methods=["post"], url_path="advance")
    def advance(self, request, pk=None):
        from apps.documents.models import Evidence

        cycle = self.get_object()
        notes = request.data.get("notes", "")
        outcome = request.data.get("outcome", "")
        evidence_id = request.data.get("evidence_id")
        evidence = None
        if evidence_id:
            evidence = Evidence.objects.filter(pk=evidence_id).first()
            if not evidence:
                return Response({"error": "Evidenza non trovata"}, status=status.HTTP_404_NOT_FOUND)
        try:
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
                }
            )
        except ValidationError as exc:
            return Response({"error": str(exc.message)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request, pk=None):
        cycle = self.get_object()
        act_description = request.data.get("act_description", "")
        try:
            cycle = services.close_cycle(cycle, request.user, act_description)
            return Response({"ok": True, "fase_corrente": "chiuso"})
        except ValidationError as exc:
            return Response({"error": str(exc.message)}, status=status.HTTP_400_BAD_REQUEST)


class PdcaPhaseViewSet(viewsets.ModelViewSet):
    queryset = PdcaPhase.objects.select_related("cycle")
    serializer_class = PdcaPhaseSerializer
    filterset_fields = ["cycle", "phase"]

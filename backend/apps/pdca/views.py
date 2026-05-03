from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.audit import log_action
from core.scoping import PlantScopedQuerysetMixin

from . import services
from .models import PdcaCycle, PdcaPhase
from .serializers import PdcaCycleSerializer, PdcaPhaseSerializer


class PdcaCycleViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = PdcaCycle.objects.select_related("plant").prefetch_related("phases")
    serializer_class = PdcaCycleSerializer
    filterset_fields = ["plant", "fase_corrente"]
    search_fields = ["title"]
    plant_field = "plant"

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
                return Response({"error": _("Evidenza non trovata")}, status=status.HTTP_404_NOT_FOUND)
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


class PdcaPhaseViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = PdcaPhase.objects.select_related("cycle")
    serializer_class = PdcaPhaseSerializer
    filterset_fields = ["cycle", "phase"]
    plant_field = "cycle__plant"

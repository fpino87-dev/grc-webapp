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


class ControlInstanceViewSet(viewsets.ModelViewSet):
    queryset = ControlInstance.objects.select_related(
        "plant", "control__framework", "control__domain"
    ).prefetch_related(
        "control__mappings_from__target_control__framework",
        "control__mappings_to__source_control__framework",
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

        return Response({
            "control_id": control.external_id,
            "title": control.get_title(lang),
            "domain": control.domain.get_name(lang) if control.domain else "",
            "framework": control.framework.code,
            "level": control.level,
            "description": control.translations.get(lang, {}).get("description", ""),
            "implementation_guidance": control.translations.get(lang, {}).get("guidance", ""),
            "evidence_examples": control.translations.get(lang, {}).get("evidence_examples", []),
            "mappings": mappings,
            "evaluation_history": history,
            "current_evidences": current_evidences,
        })

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


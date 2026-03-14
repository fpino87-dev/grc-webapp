from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

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


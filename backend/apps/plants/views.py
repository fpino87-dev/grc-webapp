from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import BusinessUnit, Plant, PlantFramework
from .serializers import BusinessUnitSerializer, PlantFrameworkSerializer, PlantSerializer


class BusinessUnitViewSet(viewsets.ModelViewSet):
    queryset = BusinessUnit.objects.all()
    serializer_class = BusinessUnitSerializer


class PlantViewSet(viewsets.ModelViewSet):
    queryset = Plant.objects.select_related("bu", "parent_plant")
    serializer_class = PlantSerializer

    def update(self, request, *args, **kwargs):
        from rest_framework.response import Response
        from apps.controls.models import ControlInstance
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        # Block code change if plant has ControlInstances
        new_code = request.data.get("code")
        if new_code and new_code != instance.code:
            if ControlInstance.objects.filter(plant=instance).exists():
                return Response(
                    {"error": "Impossibile cambiare il codice: il sito ha controlli collegati."},
                    status=400,
                )
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        # Warning if open incidents
        from apps.incidents.models import Incident
        open_incidents = Incident.objects.filter(plant=instance, status__in=["aperto", "in_analisi"]).count()
        data = serializer.data
        if open_incidents:
            data = dict(data)
            data["_warning"] = f"Questo sito ha {open_incidents} incidente/i aperti."
        return Response(data)


class PlantFrameworkViewSet(viewsets.ModelViewSet):
    queryset = PlantFramework.objects.select_related("plant", "framework")
    serializer_class = PlantFrameworkSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        plant_id = self.request.query_params.get("plant")
        if plant_id:
            qs = qs.filter(plant_id=plant_id)
        return qs

    def perform_create(self, serializer):
        pf = serializer.save(
            created_by=self.request.user,
            active_from=serializer.validated_data.get("active_from") or timezone.now().date(),
        )
        self._create_control_instances(pf)

    def _create_control_instances(self, plant_framework):
        from apps.controls.models import Control, ControlInstance
        controls = Control.objects.filter(
            framework=plant_framework.framework,
            deleted_at__isnull=True,
        )
        instances = [
            ControlInstance(
                plant=plant_framework.plant,
                control=control,
                status="non_valutato",
                created_by=self.request.user,
            )
            for control in controls
            if not ControlInstance.objects.filter(
                plant=plant_framework.plant, control=control
            ).exists()
        ]
        if instances:
            ControlInstance.objects.bulk_create(instances)

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        pf = self.get_object()
        pf.active = not pf.active
        pf.save(update_fields=["active", "updated_at"])
        return Response(PlantFrameworkSerializer(pf).data)


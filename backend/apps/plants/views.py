import os

from django.utils import timezone
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404, HttpResponseRedirect
from rest_framework import viewsets, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.translation import gettext as _

from core.audit import log_action
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

    @action(
        detail=True,
        methods=["post"],
        url_path="upload-logo",
        parser_classes=[parsers.MultiPartParser],
    )
    def upload_logo(self, request, pk=None):
        """
        Carica un file logo per il Plant usando lo stesso storage centralizzato dei documenti.
        Il file viene salvato e l'URL risultante viene scritto in Plant.logo_url.
        """
        plant = self.get_object()
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response({"error": _("Nessun file fornito.")}, status=status.HTTP_400_BAD_REQUEST)

        # Salva nel default_storage sotto una cartella dedicata ai plant
        path = default_storage.save(f"plant-logos/{plant.id}/{uploaded_file.name}", uploaded_file)
        logo_url = default_storage.url(path)

        plant.logo_url = logo_url
        plant.save(update_fields=["logo_url", "updated_at"])

        log_action(
            user=request.user,
            action_code="plants.logo.upload",
            level="L2",
            entity=plant,
            payload={"logo_url": plant.logo_url},
        )

        serializer = self.get_serializer(plant)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="logo")
    def logo(self, request, pk=None):
        """
        Restituisce il logo del plant passando sempre dal proxy API.
        Se logo_url è esterno effettua redirect; se è relativo/locale serve il file da default_storage.
        """
        plant = self.get_object()
        logo_url = (plant.logo_url or "").strip()
        if not logo_url:
            raise Http404(_("Nessun logo configurato per questo sito."))

        if logo_url.startswith("http://") or logo_url.startswith("https://"):
            return HttpResponseRedirect(logo_url)

        storage_path = logo_url
        if "/media/" in logo_url:
            storage_path = logo_url.split("/media/", 1)[1]
        storage_path = storage_path.lstrip("/")

        if not storage_path or not default_storage.exists(storage_path):
            raise Http404(_("Logo non trovato nello storage."))

        file_handle = default_storage.open(storage_path, "rb")
        filename = os.path.basename(storage_path) or "logo"
        return FileResponse(file_handle, as_attachment=False, filename=filename)


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


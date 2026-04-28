import os

from django.utils import timezone
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from rest_framework import viewsets, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.translation import gettext as _

from core.audit import log_action
from core.uploads import validate_uploaded_file
from .models import BusinessUnit, Plant, PlantFramework
from .serializers import BusinessUnitSerializer, PlantFrameworkSerializer, PlantSerializer
from .services import delete_plant

# Logo plant: solo immagini, max 2MB. SVG escluso per evitare XSS via inline script.
_LOGO_MAX_SIZE = 2 * 1024 * 1024
_LOGO_ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
_LOGO_ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}


def _validate_logo_file(uploaded_file):
    """Wrapper sopra core.uploads con whitelist logo-specific."""
    validate_uploaded_file(
        uploaded_file,
        allowed_extensions=_LOGO_ALLOWED_EXTENSIONS,
        allowed_mimes=_LOGO_ALLOWED_MIME_TYPES,
        max_bytes=_LOGO_MAX_SIZE,
    )


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

    def destroy(self, request, *args, **kwargs):
        """
        Soft delete del sito produttivo (Plant).
        L'operazione è bloccata se esistono dipendenze attive collegate al plant.
        """
        from django.core.exceptions import ValidationError

        plant = self.get_object()
        force = request.query_params.get("force") == "true"
        try:
            delete_plant(plant, request.user, force=force)
        except ValidationError as e:
            data = {"detail": str(e.message)}
            if getattr(e, "params", None) and "blocking" in e.params:
                data["blocking"] = e.params["blocking"]
            return Response(data, status=400)
        return Response(status=204)

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

        _validate_logo_file(uploaded_file)

        # Salva nel default_storage sotto una cartella dedicata ai plant
        # Il nome file viene sanificato: solo basename senza path traversal
        safe_name = os.path.basename(uploaded_file.name)
        path = default_storage.save(f"plant-logos/{plant.id}/{safe_name}", uploaded_file)
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
        Serve il logo del plant direttamente dallo storage interno.
        Non viene mai eseguito un redirect verso URL esterne per prevenire
        open redirect (CWE-601). Se logo_url è un URL assoluto esterno
        restituisce 404 — il logo deve essere caricato tramite upload-logo.
        """
        plant = self.get_object()
        logo_url = (plant.logo_url or "").strip()
        if not logo_url:
            raise Http404(_("Nessun logo configurato per questo sito."))

        # Rifiuta URL esterne: impedisce open redirect e SSRF
        if logo_url.startswith("http://") or logo_url.startswith("https://"):
            raise Http404(_("Logo non disponibile: usa l'upload file per i loghi del sito."))

        storage_path = logo_url
        if "/media/" in logo_url:
            storage_path = logo_url.split("/media/", 1)[1]
        storage_path = storage_path.lstrip("/")

        # Prevenzione path traversal: il path deve stare sotto plant-logos/
        safe_prefix = f"plant-logos/{plant.id}/"
        if not storage_path.startswith(safe_prefix):
            raise Http404(_("Logo non trovato nello storage."))

        if not default_storage.exists(storage_path):
            raise Http404(_("Logo non trovato nello storage."))

        import mimetypes
        file_handle = default_storage.open(storage_path, "rb")
        filename = os.path.basename(storage_path) or "logo"
        content_type, _ = mimetypes.guess_type(filename)
        content_type = content_type or "application/octet-stream"
        return FileResponse(
            file_handle,
            as_attachment=False,
            filename=filename,
            content_type=content_type,
        )


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
        # newfix S10 — se esiste un PlantFramework soft-deleted con stesso
        # (plant, framework) lo "ri-attiviamo" invece di tentare l'INSERT
        # (il vincolo unique_together sul DB ignora il soft-delete e farebbe
        # raise IntegrityError).
        plant = serializer.validated_data.get("plant")
        framework = serializer.validated_data.get("framework")
        active_from = serializer.validated_data.get("active_from") or timezone.now().date()
        existing = (
            PlantFramework.objects.all_with_deleted()
            .filter(plant=plant, framework=framework, deleted_at__isnull=False)
            .first()
        )
        if existing is not None:
            existing.deleted_at = None
            existing.active = True
            existing.active_from = active_from
            existing.level = serializer.validated_data.get("level", "")
            existing.save(update_fields=["deleted_at", "active", "active_from", "level", "updated_at"])
            self._create_control_instances(existing)
            serializer.instance = existing
            return
        pf = serializer.save(
            created_by=self.request.user,
            active_from=active_from,
        )
        self._create_control_instances(pf)

    def _create_control_instances(self, plant_framework):
        from apps.controls.models import Control, ControlInstance
        plant = plant_framework.plant
        controls = Control.objects.filter(
            framework=plant_framework.framework,
            deleted_at__isnull=True,
        )
        if plant_framework.framework.code == "ACN_NIS2" and plant.nis2_scope == "importante":
            controls = controls.filter(level="")
        instances = [
            ControlInstance(
                plant=plant,
                control=control,
                status="non_valutato",
                created_by=self.request.user,
            )
            for control in controls
            if not ControlInstance.objects.filter(
                plant=plant, control=control
            ).exists()
        ]
        if instances:
            ControlInstance.objects.bulk_create(instances)

    def perform_destroy(self, instance):
        from apps.controls.models import ControlInstance
        # Soft-delete tutte le ControlInstances del plant+framework, incluse quelle già valutate
        ControlInstance.objects.filter(
            plant=instance.plant,
            control__framework=instance.framework,
            deleted_at__isnull=True,
        ).update(deleted_at=timezone.now())
        log_action(
            user=self.request.user,
            action_code="plants.framework.remove",
            level="L2",
            entity=instance.plant,
            payload={"framework": instance.framework.code},
        )
        # newfix S10 — soft-delete invece di hard-delete (CLAUDE.md regola #5).
        # Un PlantFramework rimosso resta tracciabile per audit; la riassegna-
        # zione successiva lo "riattiva" via perform_create.
        instance.soft_delete()

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        pf = self.get_object()
        pf.active = not pf.active
        pf.save(update_fields=["active", "updated_at"])
        return Response(PlantFrameworkSerializer(pf).data)


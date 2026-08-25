from django.core.exceptions import ValidationError
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.translation import gettext as _

from core.audit import log_action
from core.scoping import PlantScopedQuerysetMixin
from core.viewsets import SoftDeleteAuditMixin

from .models import AssetDependency, AssetFacility, AssetIT, AssetOT, AssetSW, NetworkZone
from .permissions import AssetPermission
from .serializers import (
    AssetDependencySerializer,
    AssetFacilitySerializer,
    AssetITSerializer,
    AssetOTSerializer,
    AssetSWSerializer,
    NetworkZoneSerializer,
)
from .services import clear_revaluation_flag, delete_asset, get_eol_assets, register_change


class NetworkZoneViewSet(SoftDeleteAuditMixin, PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = NetworkZone.objects.select_related("plant")
    serializer_class = NetworkZoneSerializer
    permission_classes = [AssetPermission]
    filterset_fields = ["plant"]
    audit_action = "assets.network_zone"

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="assets.network_zone.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id)},
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(
            user=self.request.user,
            action_code="assets.network_zone.update",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id)},
        )


class MaintenanceActionsMixin:
    """Registrazione della manutenzione, uguale per ogni tipo di asset."""

    @action(detail=True, methods=["post"], url_path="record-maintenance")
    def record_maintenance_action(self, request, pk=None):
        from django.utils.dateparse import parse_date

        from .models import Asset
        from .services import record_maintenance

        asset = self.get_object()
        if not asset.maintenance_frequency_months:
            return Response(
                {"error": _("Nessuna cadenza di manutenzione configurata per questo asset.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = request.data.get("result", "superata")
        if result not in dict(Asset.MAINTENANCE_RESULT_CHOICES):
            return Response({"error": _("Esito non valido.")}, status=status.HTTP_400_BAD_REQUEST)

        date = request.data.get("date")
        if date:
            date = parse_date(str(date))
            if date is None:
                return Response(
                    {"error": _("Data non valida (formato atteso AAAA-MM-GG).")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        record_maintenance(
            asset,
            request.user,
            date=date,
            result=result,
            notes=request.data.get("notes", ""),
        )
        return Response(self.get_serializer(asset).data)

    @action(detail=False, methods=["get"], url_path="maintenance-due")
    def maintenance_due(self, request):
        """Asset con manutenzione scaduta o senza data: la lista da lavorare."""
        from django.utils import timezone

        qs = self.get_queryset().filter(
            next_maintenance_date__isnull=False,
            next_maintenance_date__lt=timezone.localdate(),
        )
        plant_id = request.query_params.get("plant")
        if plant_id:
            qs = qs.filter(plant_id=plant_id)
        return Response(self.get_serializer(qs, many=True).data)


class AssetITViewSet(MaintenanceActionsMixin, PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = AssetIT.objects.select_related("plant", "owner")
    serializer_class = AssetITSerializer
    permission_classes = [AssetPermission]
    filterset_fields = ["plant", "internet_exposed", "eol_date"]

    def perform_create(self, serializer):
        instance = serializer.save(asset_type="IT", created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="assets.asset_it.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "name": instance.name},
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(
            user=self.request.user,
            action_code="assets.asset_it.update",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "name": instance.name},
        )

    def destroy(self, request, *args, **kwargs):
        asset = self.get_object()
        try:
            delete_asset(asset, request.user)
        except ValidationError as e:
            return Response(
                {"detail": e.messages[0] if getattr(e, "messages", None) else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="eol")
    def eol(self, request):
        qs = get_eol_assets()
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="register-change")
    def register_change_action(self, request, pk=None):
        asset = self.get_object()
        change_ref = request.data.get("change_ref", "")
        if not change_ref:
            return Response({"error": _("change_ref obbligatorio")}, status=400)
        result = register_change(
            asset=asset,
            user=request.user,
            change_ref=change_ref,
            change_desc=request.data.get("change_desc", ""),
            portal_url=request.data.get("portal_url", ""),
        )
        return Response(result)

    @action(detail=True, methods=["post"], url_path="clear-revaluation")
    def clear_revaluation(self, request, pk=None):
        asset = self.get_object()
        clear_revaluation_flag(asset, request.user, request.data.get("notes", ""))
        return Response({"ok": True})

    @action(detail=False, methods=["get"], url_path="needs-revaluation")
    def needs_revaluation_list(self, request):
        plant_id = request.query_params.get("plant")
        qs = self.get_queryset().filter(needs_revaluation=True)
        if plant_id:
            qs = qs.filter(plant_id=plant_id)
        return Response(self.get_serializer(qs, many=True).data)


class AssetOTViewSet(MaintenanceActionsMixin, PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = AssetOT.objects.select_related("plant", "owner", "network_zone")
    serializer_class = AssetOTSerializer
    permission_classes = [AssetPermission]
    filterset_fields = ["plant"]

    def perform_create(self, serializer):
        instance = serializer.save(asset_type="OT", created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="assets.asset_ot.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "name": instance.name},
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(
            user=self.request.user,
            action_code="assets.asset_ot.update",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "name": instance.name},
        )

    def destroy(self, request, *args, **kwargs):
        asset = self.get_object()
        try:
            delete_asset(asset, request.user)
        except ValidationError as e:
            return Response(
                {"detail": e.messages[0] if getattr(e, "messages", None) else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="register-change")
    def register_change_action(self, request, pk=None):
        asset = self.get_object()
        change_ref = request.data.get("change_ref", "")
        if not change_ref:
            return Response({"error": _("change_ref obbligatorio")}, status=400)
        result = register_change(
            asset=asset,
            user=request.user,
            change_ref=change_ref,
            change_desc=request.data.get("change_desc", ""),
            portal_url=request.data.get("portal_url", ""),
        )
        return Response(result)

    @action(detail=True, methods=["post"], url_path="clear-revaluation")
    def clear_revaluation(self, request, pk=None):
        asset = self.get_object()
        clear_revaluation_flag(asset, request.user, request.data.get("notes", ""))
        return Response({"ok": True})

    @action(detail=False, methods=["get"], url_path="needs-revaluation")
    def needs_revaluation_list(self, request):
        plant_id = request.query_params.get("plant")
        qs = self.get_queryset().filter(needs_revaluation=True)
        if plant_id:
            qs = qs.filter(plant_id=plant_id)
        return Response(self.get_serializer(qs, many=True).data)


class AssetSWViewSet(MaintenanceActionsMixin, PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = AssetSW.objects.select_related("plant", "owner")
    serializer_class = AssetSWSerializer
    permission_classes = [AssetPermission]
    filterset_fields = ["plant", "approval_status"]

    def perform_create(self, serializer):
        instance = serializer.save(asset_type="SW", created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="assets.asset_sw.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "name": instance.name},
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(
            user=self.request.user,
            action_code="assets.asset_sw.update",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "name": instance.name},
        )

    def destroy(self, request, *args, **kwargs):
        asset = self.get_object()
        try:
            delete_asset(asset, request.user)
        except ValidationError as e:
            return Response(
                {"detail": e.messages[0] if getattr(e, "messages", None) else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AssetFacilityViewSet(MaintenanceActionsMixin, PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    """Impianti di supporto: continuità elettrica, antincendio, climatizzazione,
    sicurezza fisica. Nessuna gestione di change: un impianto non si "patcha",
    si manutiene — il ciclo di vita è quello della manutenzione periodica."""

    queryset = AssetFacility.objects.select_related(
        "plant", "owner", "maintainer_supplier"
    ).prefetch_related("serves_assets")
    serializer_class = AssetFacilitySerializer
    permission_classes = [AssetPermission]
    filterset_fields = ["plant", "category", "criticality"]
    search_fields = ["name", "location", "vendor", "model", "serial_number"]

    def perform_create(self, serializer):
        instance = serializer.save(asset_type="FAC", created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="assets.asset_facility.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "name": instance.name, "category": instance.category},
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(
            user=self.request.user,
            action_code="assets.asset_facility.update",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "name": instance.name},
        )

    def destroy(self, request, *args, **kwargs):
        asset = self.get_object()
        try:
            delete_asset(asset, request.user)
        except ValidationError as e:
            return Response(
                {"detail": e.messages[0] if getattr(e, "messages", None) else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AssetDependencyViewSet(SoftDeleteAuditMixin, PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = AssetDependency.objects.select_related("from_asset__plant", "to_asset__plant")
    serializer_class = AssetDependencySerializer
    permission_classes = [AssetPermission]
    plant_field = "from_asset__plant"
    audit_action = "assets.asset_dependency"

    def get_queryset(self):
        qs = super().get_queryset()
        plant = self.request.query_params.get("plant")
        if plant:
            qs = qs.filter(from_asset__plant_id=plant)
        return qs

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="assets.asset_dependency.create",
            level="L1",
            entity=instance,
            payload={"id": str(instance.id)},
        )

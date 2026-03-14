from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.audit import log_action

from .models import AssetDependency, AssetIT, AssetOT, NetworkZone
from .serializers import (
    AssetDependencySerializer,
    AssetITSerializer,
    AssetOTSerializer,
    NetworkZoneSerializer,
)
from .services import get_eol_assets


class NetworkZoneViewSet(viewsets.ModelViewSet):
    queryset = NetworkZone.objects.select_related("plant")
    serializer_class = NetworkZoneSerializer
    filterset_fields = ["plant"]

    def perform_create(self, serializer):
        instance = serializer.save()
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


class AssetITViewSet(viewsets.ModelViewSet):
    queryset = AssetIT.objects.select_related("plant", "owner")
    serializer_class = AssetITSerializer
    filterset_fields = ["plant", "internet_exposed", "eol_date"]

    def perform_create(self, serializer):
        instance = serializer.save(asset_type="IT")
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

    @action(detail=False, methods=["get"], url_path="eol")
    def eol(self, request):
        qs = get_eol_assets()
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class AssetOTViewSet(viewsets.ModelViewSet):
    queryset = AssetOT.objects.select_related("plant", "owner", "network_zone")
    serializer_class = AssetOTSerializer
    filterset_fields = ["plant"]

    def perform_create(self, serializer):
        instance = serializer.save(asset_type="OT")
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


class AssetDependencyViewSet(viewsets.ModelViewSet):
    queryset = AssetDependency.objects.select_related("from_asset__plant", "to_asset__plant")
    serializer_class = AssetDependencySerializer

    def get_queryset(self):
        qs = super().get_queryset()
        plant = self.request.query_params.get("plant")
        if plant:
            qs = qs.filter(from_asset__plant_id=plant)
        return qs

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(
            user=self.request.user,
            action_code="assets.asset_dependency.create",
            level="L1",
            entity=instance,
            payload={"id": str(instance.id)},
        )

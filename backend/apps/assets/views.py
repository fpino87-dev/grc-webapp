from django.core.exceptions import ValidationError
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.translation import gettext as _

from core.audit import log_action

from .models import AssetDependency, AssetIT, AssetOT, NetworkZone
from .serializers import (
    AssetDependencySerializer,
    AssetITSerializer,
    AssetOTSerializer,
    NetworkZoneSerializer,
)
from .services import clear_revaluation_flag, delete_asset, get_eol_assets, register_change


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

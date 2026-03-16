from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from . import services
from .models import (
    DEFAULT_ROLE_PROFILES,
    EVENT_LABELS,
    NOTIFICATION_PROFILES,
    EmailConfiguration,
    NotificationRule,
    NotificationRoleProfile,
    NotificationSubscription,
)
from .serializers import (
    EmailConfigurationReadSerializer,
    EmailConfigurationSerializer,
    NotificationRoleProfileSerializer,
    NotificationRuleSerializer,
    NotificationSubscriptionSerializer,
)


class NotificationSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = NotificationSubscription.objects.select_related("user")
    serializer_class = NotificationSubscriptionSerializer
    filterset_fields = ["user", "event_type", "channel"]

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, created_by=self.request.user)


class EmailConfigurationViewSet(viewsets.ModelViewSet):
    queryset = EmailConfiguration.objects.all()
    serializer_class = EmailConfigurationSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return EmailConfigurationReadSerializer
        return EmailConfigurationSerializer

    @action(detail=True, methods=["post"], url_path="test")
    def test_connection(self, request, pk=None):
        config = self.get_object()
        ok, error = services.test_email_connection(config)
        if ok:
            return Response({"ok": True, "message": "Email di test inviata correttamente a " + config.username})
        return Response({"ok": False, "error": error}, status=400)

    @action(detail=False, methods=["get"], url_path="presets")
    def presets(self, request):
        return Response(EmailConfiguration.PROVIDER_PRESETS)


class NotificationRuleViewSet(viewsets.ModelViewSet):
    queryset = NotificationRule.objects.select_related("scope_bu", "scope_plant")
    serializer_class = NotificationRuleSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["event_type", "enabled", "scope_type"]


class NotificationRoleProfileViewSet(viewsets.ModelViewSet):
    queryset = NotificationRoleProfile.objects.all()
    serializer_class = NotificationRoleProfileSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["grc_role", "profile", "enabled"]

    @action(detail=False, methods=["get"], url_path="profiles-catalog")
    def profiles_catalog(self, request):
        return Response({
            "profiles":     NOTIFICATION_PROFILES,
            "event_labels": EVENT_LABELS,
        })

    @action(detail=False, methods=["post"], url_path="reset-defaults")
    def reset_defaults(self, request):
        updated = 0
        for role, profile in DEFAULT_ROLE_PROFILES.items():
            n = NotificationRoleProfile.objects.filter(grc_role=role).update(
                profile=profile, enabled=True, custom_events=[]
            )
            updated += n
        return Response({"ok": True, "updated": updated, "message": f"{updated} profili reimpostati ai valori default"})

    @action(detail=True, methods=["post"], url_path="set-custom")
    def set_custom(self, request, pk=None):
        profile_obj = self.get_object()
        events = request.data.get("events", [])
        valid_events = list(EVENT_LABELS.keys())
        invalid = [e for e in events if e not in valid_events]
        if invalid:
            return Response(
                {"error": f"Eventi non validi: {invalid}. Usa uno di: {valid_events}"},
                status=400,
            )
        profile_obj.profile = "custom"
        profile_obj.custom_events = events
        profile_obj.save(update_fields=["profile", "custom_events", "updated_at"])
        return Response({"ok": True, "profile": "custom", "active_events": profile_obj.get_active_events()})

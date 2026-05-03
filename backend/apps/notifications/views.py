from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.auth_grc.permissions import IsGrcSuperAdmin
from core.audit import log_action

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


# newfix F2 — campi sensibili la cui modifica deve produrre audit `notif.smtp.config.changed`.
# Il payload non contiene mai la password (campo write-only nel serializer + censurato qui).
_SMTP_AUDITED_FIELDS = (
    "host", "port", "username", "use_tls", "use_ssl",
    "from_email", "reply_to", "use_auth", "blank_username",
)


def _smtp_audit_payload(config: "EmailConfiguration", event: str) -> dict:
    return {
        "event": event,
        "config_id": str(config.pk),
        "host": config.host,
        "port": config.port,
        "username_present": bool((config.username or "").strip()),
        "use_tls": config.use_tls,
        "use_ssl": config.use_ssl,
        "from_email": config.from_email,
    }


class EmailConfigurationViewSet(viewsets.ModelViewSet):
    queryset = EmailConfiguration.objects.all()
    serializer_class = EmailConfigurationSerializer
    permission_classes = [IsAuthenticated, IsGrcSuperAdmin]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return EmailConfigurationReadSerializer
        return EmailConfigurationSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(
            user=self.request.user,
            action_code="notif.smtp.config.changed",
            level="L2",
            entity=instance,
            payload=_smtp_audit_payload(instance, "created"),
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(
            user=self.request.user,
            action_code="notif.smtp.config.changed",
            level="L2",
            entity=instance,
            payload=_smtp_audit_payload(instance, "updated"),
        )

    def perform_destroy(self, instance):
        log_action(
            user=self.request.user,
            action_code="notif.smtp.config.changed",
            level="L2",
            entity=instance,
            payload=_smtp_audit_payload(instance, "deleted"),
        )
        instance.delete()

    @action(detail=True, methods=["post"], url_path="test")
    def test_connection(self, request, pk=None):
        config = self.get_object()
        recipient = request.data.get("recipient", "")
        ok, error = services.test_email_connection(config, test_recipient=recipient)
        if ok:
            return Response({"ok": True, "message": f"Email di test inviata a {recipient}"})
        return Response({"ok": False, "error": error}, status=400)

    @action(detail=False, methods=["get"], url_path="presets")
    def presets(self, request):
        return Response(EmailConfiguration.PROVIDER_PRESETS)


class NotificationRuleViewSet(viewsets.ModelViewSet):
    queryset = NotificationRule.objects.select_related("scope_bu", "scope_plant")
    serializer_class = NotificationRuleSerializer
    permission_classes = [IsAuthenticated, IsGrcSuperAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["event_type", "enabled", "scope_type"]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(
            user=self.request.user,
            action_code="notif.smtp.config.changed",
            level="L2",
            entity=instance,
            payload={"event": "rule_created", "rule_id": str(instance.pk),
                     "event_type": instance.event_type, "enabled": instance.enabled,
                     "scope_type": instance.scope_type},
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(
            user=self.request.user,
            action_code="notif.smtp.config.changed",
            level="L2",
            entity=instance,
            payload={"event": "rule_updated", "rule_id": str(instance.pk),
                     "event_type": instance.event_type, "enabled": instance.enabled,
                     "scope_type": instance.scope_type},
        )


class NotificationRoleProfileViewSet(viewsets.ModelViewSet):
    queryset = NotificationRoleProfile.objects.all()
    serializer_class = NotificationRoleProfileSerializer
    permission_classes = [IsAuthenticated, IsGrcSuperAdmin]
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

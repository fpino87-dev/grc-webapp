from rest_framework import serializers

from .models import (
    EmailConfiguration,
    NotificationRule,
    NotificationRoleProfile,
    NotificationSubscription,
    NOTIFICATION_PROFILES,
)


class NotificationSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationSubscription
        fields = [
            "id",
            "user",
            "event_type",
            "channel",
            "enabled",
            "config",
            "created_at",
            "updated_at",
            "created_by",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at", "created_by"]


class EmailConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailConfiguration
        fields = [
            "id",
            "name",
            "provider",
            "host",
            "port",
            "use_tls",
            "use_ssl",
            "username",
            "password",
            "from_email",
            "active",
            "last_test_at",
            "last_test_ok",
            "last_test_error",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {"password": {"write_only": True}}


class EmailConfigurationReadSerializer(serializers.ModelSerializer):
    """Versione senza password per GET."""

    class Meta:
        model = EmailConfiguration
        fields = [
            "id",
            "name",
            "provider",
            "host",
            "port",
            "use_tls",
            "use_ssl",
            "username",
            "from_email",
            "active",
            "last_test_at",
            "last_test_ok",
            "last_test_error",
            "created_at",
            "updated_at",
        ]


class NotificationRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationRule
        fields = [
            "id",
            "event_type",
            "enabled",
            "recipient_roles",
            "scope_type",
            "scope_bu",
            "scope_plant",
            "channel",
            "created_at",
            "updated_at",
            "created_by",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "created_by"]


class NotificationRoleProfileSerializer(serializers.ModelSerializer):
    active_events = serializers.SerializerMethodField(read_only=True)
    profile_label = serializers.SerializerMethodField(read_only=True)

    def get_active_events(self, obj):
        return obj.get_active_events()

    def get_profile_label(self, obj):
        if obj.profile == "custom":
            return "Personalizzato"
        return NOTIFICATION_PROFILES.get(obj.profile, {}).get("label", obj.profile)

    class Meta:
        model = NotificationRoleProfile
        fields = [
            "id",
            "grc_role",
            "profile",
            "profile_label",
            "custom_events",
            "enabled",
            "active_events",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

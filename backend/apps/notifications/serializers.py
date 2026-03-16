from rest_framework import serializers

from .models import EmailConfiguration, NotificationSubscription


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

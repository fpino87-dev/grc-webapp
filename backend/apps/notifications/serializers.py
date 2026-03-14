from rest_framework import serializers

from .models import NotificationSubscription


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

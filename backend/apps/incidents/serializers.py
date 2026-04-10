from rest_framework import serializers

from .models import Incident, IncidentNotification, NIS2Configuration, NIS2Notification, RCA


class IncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Incident
        fields = "__all__"


class IncidentNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentNotification
        fields = "__all__"


class RCASerializer(serializers.ModelSerializer):
    class Meta:
        model = RCA
        fields = "__all__"


class NIS2NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = NIS2Notification
        fields = "__all__"


class NIS2ConfigurationSerializer(serializers.ModelSerializer):
    """Solo parametri di calcolo significatività — anagrafica NIS2 è sul Plant (M01)."""

    class Meta:
        model = NIS2Configuration
        fields = [
            "id",
            "plant",
            "threshold_users",
            "threshold_hours",
            "threshold_financial",
            "multiplier_medium",
            "multiplier_high",
            "recurrence_window_days",
            "recurrence_score_bonus",
            "ptnr_threshold",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


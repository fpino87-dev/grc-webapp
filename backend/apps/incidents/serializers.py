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
    class Meta:
        model = NIS2Configuration
        fields = "__all__"


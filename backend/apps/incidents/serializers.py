from rest_framework import serializers

from .models import Incident, IncidentNotification, RCA


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


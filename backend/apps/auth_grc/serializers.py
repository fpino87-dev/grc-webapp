from rest_framework import serializers

from .models import ExternalAuditorToken, UserPlantAccess


class UserPlantAccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPlantAccess
        fields = "__all__"


class ExternalAuditorTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalAuditorToken
        fields = "__all__"


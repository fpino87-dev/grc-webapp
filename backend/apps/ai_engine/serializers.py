from rest_framework import serializers

from .models import AiInteractionLog, AiProviderConfig


class AiInteractionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AiInteractionLog
        fields = "__all__"


class AiProviderConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AiProviderConfig
        fields = "__all__"


class AiProviderConfigReadSerializer(serializers.ModelSerializer):
    api_key = serializers.SerializerMethodField(read_only=True)
    budget_remaining = serializers.IntegerField(read_only=True)
    budget_pct = serializers.FloatField(read_only=True)

    class Meta:
        model = AiProviderConfig
        fields = "__all__"

    def get_api_key(self, obj):
        return "********" if obj.api_key else ""

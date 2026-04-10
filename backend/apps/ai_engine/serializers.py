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

    def update(self, instance, validated_data):
        # Non sovrascrivere la api_key se arriva stringa vuota
        if "api_key" in validated_data and not validated_data["api_key"]:
            validated_data.pop("api_key")
        return super().update(instance, validated_data)


class AiProviderConfigReadSerializer(serializers.ModelSerializer):
    api_key = serializers.SerializerMethodField(read_only=True)
    budget_remaining = serializers.IntegerField(read_only=True)
    budget_pct = serializers.FloatField(read_only=True)

    class Meta:
        model = AiProviderConfig
        fields = "__all__"

    def get_api_key(self, obj):
        return "********" if obj.api_key else ""

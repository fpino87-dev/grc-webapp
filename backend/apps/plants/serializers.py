from rest_framework import serializers

from .models import BusinessUnit, Plant, PlantFramework


class BusinessUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessUnit
        fields = "__all__"


class PlantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plant
        fields = "__all__"


class PlantFrameworkSerializer(serializers.ModelSerializer):
    framework_code = serializers.CharField(source="framework.code", read_only=True)
    framework_name = serializers.CharField(source="framework.name", read_only=True)

    class Meta:
        model = PlantFramework
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "created_by", "active_from"]


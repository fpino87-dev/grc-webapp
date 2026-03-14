from rest_framework import serializers

from .models import Control, ControlDomain, ControlInstance, Framework


class FrameworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Framework
        fields = "__all__"


class ControlDomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = ControlDomain
        fields = "__all__"


class ControlSerializer(serializers.ModelSerializer):
    class Meta:
        model = Control
        fields = "__all__"


class ControlInstanceSerializer(serializers.ModelSerializer):
    control_external_id = serializers.CharField(source="control.external_id", read_only=True)
    control_title = serializers.SerializerMethodField()
    framework_code = serializers.CharField(source="control.framework.code", read_only=True)
    mapped_controls = serializers.SerializerMethodField()

    class Meta:
        model = ControlInstance
        fields = "__all__"

    def get_control_title(self, obj):
        return obj.control.get_title("it")

    def get_mapped_controls(self, obj):
        result = []
        for m in obj.control.mappings_from.all():
            result.append({
                "external_id": m.target_control.external_id,
                "framework_code": m.target_control.framework.code,
                "relationship": m.relationship,
            })
        for m in obj.control.mappings_to.all():
            result.append({
                "external_id": m.source_control.external_id,
                "framework_code": m.source_control.framework.code,
                "relationship": m.relationship,
            })
        return result


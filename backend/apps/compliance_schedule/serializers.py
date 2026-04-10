from rest_framework import serializers
from .models import ComplianceSchedulePolicy, ScheduleRule, RequiredDocument, RULE_TYPE_LABELS


class ScheduleRuleSerializer(serializers.ModelSerializer):
    rule_type_label = serializers.SerializerMethodField()

    class Meta:
        model = ScheduleRule
        fields = [
            "id", "rule_type", "rule_type_label",
            "frequency_value", "frequency_unit",
            "alert_days_before", "enabled",
        ]

    def get_rule_type_label(self, obj):
        return RULE_TYPE_LABELS.get(obj.rule_type, obj.rule_type)


class ComplianceSchedulePolicySerializer(serializers.ModelSerializer):
    rules = ScheduleRuleSerializer(many=True, read_only=True)
    plant_name = serializers.CharField(source="plant.name", read_only=True, default=None)

    class Meta:
        model = ComplianceSchedulePolicy
        fields = [
            "id", "plant", "plant_name", "name",
            "is_active", "valid_from", "notes", "rules",
        ]


class RequiredDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequiredDocument
        fields = [
            "id", "framework", "document_type", "description",
            "iso_clause", "mandatory", "notes",
        ]

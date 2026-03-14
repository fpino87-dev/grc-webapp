from rest_framework import serializers

from .models import RiskAssessment, RiskDimension, RiskMitigationPlan


class RiskAssessmentSerializer(serializers.ModelSerializer):
    plant_name = serializers.CharField(source="plant.name", read_only=True)
    asset_name = serializers.CharField(source="asset.name", read_only=True)
    assessed_by_username = serializers.CharField(source="assessed_by.username", read_only=True)
    accepted_by_username = serializers.CharField(source="accepted_by.username", read_only=True)
    risk_level = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = RiskAssessment
        fields = [
            "id",
            "plant", "plant_name",
            "asset", "asset_name",
            "name", "threat_category",
            "assessment_type",
            "probability", "impact",
            "treatment",
            "status",
            "assessed_by", "assessed_by_username",
            "assessed_at",
            "score",
            "ale_annuo",
            "risk_accepted",
            "accepted_by", "accepted_by_username",
            "plan_due_date",
            "risk_level",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "created_at", "updated_at",
            "plant_name", "asset_name",
            "assessed_by_username", "accepted_by_username",
            "risk_level", "score",
        ]

    def get_risk_level(self, obj):
        return obj.risk_level


class RiskDimensionSerializer(serializers.ModelSerializer):
    assessment_type = serializers.CharField(source="assessment.assessment_type", read_only=True)

    class Meta:
        model = RiskDimension
        fields = [
            "id",
            "assessment",
            "assessment_type",
            "dimension_code",
            "value",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "assessment_type"]


class RiskMitigationPlanSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source="owner.username", read_only=True)

    class Meta:
        model = RiskMitigationPlan
        fields = [
            "id",
            "assessment",
            "action",
            "owner",
            "owner_username",
            "due_date",
            "completed_at",
            "control_instance",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "owner_username"]

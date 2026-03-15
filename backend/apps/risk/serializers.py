from rest_framework import serializers

from .models import RiskAppetitePolicy, RiskAssessment, RiskDimension, RiskMitigationPlan


class RiskAssessmentSerializer(serializers.ModelSerializer):
    plant_name = serializers.CharField(source="plant.name", read_only=True)
    asset_name = serializers.CharField(source="asset.name", read_only=True)
    assessed_by_username = serializers.CharField(source="assessed_by.username", read_only=True)
    accepted_by_username = serializers.CharField(source="accepted_by.username", read_only=True)
    risk_level = serializers.SerializerMethodField(read_only=True)
    owner_name = serializers.SerializerMethodField(read_only=True)
    critical_process_name = serializers.CharField(source="critical_process.name", read_only=True)
    ale_calcolato = serializers.SerializerMethodField(read_only=True)
    weighted_score = serializers.SerializerMethodField(read_only=True)
    inherent_risk_level = serializers.SerializerMethodField(read_only=True)
    risk_reduction_pct = serializers.SerializerMethodField(read_only=True)
    accepted_by_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = RiskAssessment
        fields = [
            "id",
            "plant", "plant_name",
            "asset", "asset_name",
            "name", "threat_category",
            "assessment_type",
            "probability", "impact",
            "inherent_probability", "inherent_impact", "inherent_score",
            "treatment",
            "status",
            "assessed_by", "assessed_by_username",
            "assessed_at",
            "owner", "owner_name",
            "critical_process", "critical_process_name",
            "score",
            "ale_annuo",
            "ale_calcolato",
            "weighted_score",
            "risk_accepted",
            "accepted_by", "accepted_by_username",
            "risk_accepted_formally",
            "risk_accepted_by", "accepted_by_name",
            "risk_accepted_at", "risk_acceptance_note", "risk_acceptance_expiry",
            "plan_due_date",
            "risk_level", "inherent_risk_level", "risk_reduction_pct",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "created_at", "updated_at",
            "plant_name", "asset_name",
            "assessed_by_username", "accepted_by_username",
            "risk_level", "inherent_risk_level", "risk_reduction_pct",
            "score", "inherent_score",
            "owner_name", "critical_process_name",
            "ale_calcolato", "weighted_score", "accepted_by_name",
        ]

    def get_risk_level(self, obj):
        return obj.risk_level

    def get_inherent_risk_level(self, obj):
        return obj.inherent_risk_level

    def get_risk_reduction_pct(self, obj):
        return obj.risk_reduction_pct

    def get_accepted_by_name(self, obj):
        if not obj.risk_accepted_by:
            return None
        u = obj.risk_accepted_by
        return f"{u.first_name} {u.last_name}".strip() or u.email

    def get_owner_name(self, obj):
        if not obj.owner:
            return None
        return f"{obj.owner.first_name} {obj.owner.last_name}".strip() or obj.owner.email

    def get_ale_calcolato(self, obj):
        from .services import calc_ale
        val = calc_ale(obj)
        return str(val) if val else None

    def get_weighted_score(self, obj):
        return obj.weighted_score


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


class RiskAppetitePolicySerializer(serializers.ModelSerializer):
    approved_by_name = serializers.SerializerMethodField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = RiskAppetitePolicy
        fields = "__all__"

    def get_approved_by_name(self, obj):
        if not obj.approved_by:
            return None
        u = obj.approved_by
        return f"{u.first_name} {u.last_name}".strip() or u.email

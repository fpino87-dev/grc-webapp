from rest_framework import serializers

from .models import (
    InformationClass,
    RiskAppetitePolicy,
    RiskAssessment,
    RiskAssessmentCycle,
    RiskDimension,
    RiskGovernancePolicy,
    RiskMitigationPlan,
    ThreatCatalogEntry,
)
from apps.bcp.models import BcpPlan


class RiskAssessmentSerializer(serializers.ModelSerializer):
    plant_name = serializers.CharField(source="plant.name", read_only=True)
    asset_name = serializers.CharField(source="asset.name", read_only=True)
    assessed_by_username = serializers.CharField(source="assessed_by.username", read_only=True)
    accepted_by_username = serializers.CharField(source="accepted_by.username", read_only=True)
    risk_level = serializers.SerializerMethodField(read_only=True)
    owner_name = serializers.SerializerMethodField(read_only=True)
    treatment_owner_name = serializers.SerializerMethodField(read_only=True)
    critical_process_name = serializers.CharField(source="critical_process.name", read_only=True)
    ale_calcolato = serializers.SerializerMethodField(read_only=True)
    weighted_score = serializers.SerializerMethodField(read_only=True)
    inherent_risk_level = serializers.SerializerMethodField(read_only=True)
    risk_reduction_pct = serializers.SerializerMethodField(read_only=True)
    accepted_by_name = serializers.SerializerMethodField(read_only=True)
    mitigation_plans_count = serializers.SerializerMethodField(read_only=True)
    mitigation_plans_completed = serializers.SerializerMethodField(read_only=True)
    last_plan_completed_at = serializers.SerializerMethodField(read_only=True)

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
            "treatment_owner", "treatment_owner_external", "treatment_owner_name",
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
            "cause", "consequence",
            "nis2_art21_category", "nis2_relevance", "impacted_systems",
            "risk_level", "inherent_risk_level", "risk_reduction_pct",
            "mitigation_plans_count", "mitigation_plans_completed", "last_plan_completed_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "created_at", "updated_at",
            "plant_name", "asset_name",
            "assessed_by_username", "accepted_by_username",
            "risk_level", "inherent_risk_level", "risk_reduction_pct",
            "score", "inherent_score",
            "owner_name", "treatment_owner_name", "critical_process_name",
            "ale_calcolato", "weighted_score", "accepted_by_name",
            "mitigation_plans_count", "mitigation_plans_completed", "last_plan_completed_at",
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

    def get_treatment_owner_name(self, obj):
        from .services import mixed_owner_name
        return mixed_owner_name(obj.treatment_owner, obj.treatment_owner_external)

    def validate(self, attrs):
        from .services import normalize_mixed_owner
        return normalize_mixed_owner(attrs, "treatment_owner", "treatment_owner_external")

    def get_ale_calcolato(self, obj):
        from .services import calc_ale
        val = calc_ale(obj)
        return str(val) if val else None

    def get_weighted_score(self, obj):
        return obj.weighted_score

    def get_mitigation_plans_count(self, obj):
        plans = obj.mitigation_plans.all()
        return sum(1 for p in plans if p.deleted_at is None)

    def get_mitigation_plans_completed(self, obj):
        plans = obj.mitigation_plans.all()
        return sum(1 for p in plans if p.deleted_at is None and p.completed_at is not None)

    def get_last_plan_completed_at(self, obj):
        completed = [
            p.completed_at for p in obj.mitigation_plans.all()
            if p.deleted_at is None and p.completed_at is not None
        ]
        return max(completed).isoformat() if completed else None


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
    owner_name = serializers.SerializerMethodField(read_only=True)
    bcp_plan = serializers.PrimaryKeyRelatedField(
        queryset=BcpPlan.objects.all(),
        required=False,
        allow_null=True,
    )

    bcp_plan_title = serializers.SerializerMethodField(read_only=True)
    bcp_plan_status = serializers.SerializerMethodField(read_only=True)
    bcp_plan_last_test_date = serializers.SerializerMethodField(read_only=True)
    bcp_plan_next_test_date = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = RiskMitigationPlan
        fields = [
            "id",
            "assessment",
            "action",
            "owner",
            "owner_username",
            "owner_external",
            "owner_name",
            "due_date",
            "bcp_plan",
            "bcp_plan_title",
            "bcp_plan_status",
            "bcp_plan_last_test_date",
            "bcp_plan_next_test_date",
            "completed_at",
            "control_instance",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "owner_username", "owner_name", "bcp_plan_title", "bcp_plan_status", "bcp_plan_last_test_date", "bcp_plan_next_test_date"]

    def get_owner_name(self, obj):
        from .services import mixed_owner_name
        return mixed_owner_name(obj.owner, obj.owner_external)

    def validate(self, attrs):
        from .services import normalize_mixed_owner
        return normalize_mixed_owner(attrs, "owner", "owner_external")

    def get_bcp_plan_title(self, obj):
        if not obj.bcp_plan:
            return None
        return obj.bcp_plan.title

    def get_bcp_plan_status(self, obj):
        if not obj.bcp_plan:
            return None
        return obj.bcp_plan.status

    def get_bcp_plan_last_test_date(self, obj):
        if not obj.bcp_plan:
            return None
        return obj.bcp_plan.last_test_date

    def get_bcp_plan_next_test_date(self, obj):
        if not obj.bcp_plan:
            return None
        return obj.bcp_plan.next_test_date


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


# ── Metodologia D-ITA-INF-23 ─────────────────────────────────────────────────


def _request_lang(serializer) -> str:
    request = serializer.context.get("request")
    return (getattr(request, "LANGUAGE_CODE", None) if request else None) or "it"


def _user_name(user):
    if not user:
        return None
    return f"{user.first_name} {user.last_name}".strip() or user.username


class ThreatCatalogEntrySerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()

    class Meta:
        model = ThreatCatalogEntry
        fields = [
            "id", "code", "title", "asset_types", "cia", "translations",
            "source", "catalog_version", "active",
        ]
        read_only_fields = ["source", "catalog_version"]

    def get_title(self, obj):
        return obj.get_title(_request_lang(self))


class InformationClassSerializer(serializers.ModelSerializer):
    plant_name = serializers.CharField(source="plant.name", read_only=True)
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = InformationClass
        fields = [
            "id", "plant", "plant_name", "name", "description",
            "owner", "owner_name", "owner_role",
            "confidentiality", "integrity", "availability",
            "critical_processes",
        ]

    def get_owner_name(self, obj):
        return _user_name(obj.owner)

    def validate(self, attrs):
        from django.utils.translation import gettext as _

        plant = attrs.get("plant", getattr(self.instance, "plant", None))
        processes = attrs.get("critical_processes")
        if processes and plant is not None:
            if any(p.plant_id != plant.pk for p in processes):
                raise serializers.ValidationError(
                    {"critical_processes": _("I processi devono appartenere al sito della classe di informazioni.")}
                )
        return attrs


class RiskGovernancePolicySerializer(serializers.ModelSerializer):
    plant_name = serializers.CharField(source="plant.name", read_only=True)
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = RiskGovernancePolicy
        fields = [
            "id", "plant", "plant_name", "preset", "group_register_enabled",
            "acceptance_matrix", "upper_opinion", "acceptance_max_months",
            "economic_thresholds", "overdue_escalation_days", "review_frequency_months",
            "approved_by", "approved_by_name", "approved_at", "notes",
        ]
        read_only_fields = fields

    def get_approved_by_name(self, obj):
        return _user_name(obj.approved_by)


class RiskAssessmentCycleSerializer(serializers.ModelSerializer):
    plant_name = serializers.CharField(source="plant.name", read_only=True)
    approved_by_body_name = serializers.CharField(source="approved_by_body.name", read_only=True)
    risks_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = RiskAssessmentCycle
        fields = [
            "id", "plant", "plant_name", "kind", "trigger_reason", "status",
            "started_at", "closed_at", "approved_by_body", "approved_by_body_name",
            "approval_review", "approved_at", "local_adoption_ref", "risks_count",
        ]
        read_only_fields = fields

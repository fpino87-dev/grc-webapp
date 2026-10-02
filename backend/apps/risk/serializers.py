from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.assets.models import Asset
from apps.bcp.models import BcpPlan
from apps.bia.models import CriticalProcess
from apps.plants.models import Plant
from apps.suppliers.models import Supplier

from .models import (
    InformationClass,
    RiskAcceptance,
    RiskAssessment,
    RiskAssessmentCycle,
    RiskExistingMeasure,
    RiskGovernancePolicy,
    RiskLocalImpactReport,
    RiskMitigationPlan,
    ThreatCatalogEntry,
)

User = get_user_model()


def _request_lang(serializer) -> str:
    request = serializer.context.get("request")
    return (getattr(request, "LANGUAGE_CODE", None) if request else None) or "it"


def _user_name(user):
    if not user:
        return None
    return f"{user.first_name} {user.last_name}".strip() or user.username


def _control_label(serializer, control_instance):
    if not control_instance:
        return None
    ctrl = control_instance.control
    return f"{ctrl.external_id} {ctrl.get_title(_request_lang(serializer))}"


# ── Rischio ──────────────────────────────────────────────────────────────────

class RiskAssessmentSerializer(serializers.ModelSerializer):
    """Lettura del rischio. Le scritture passano dai service (vedi le viste)."""

    plant_name = serializers.CharField(source="plant.name", read_only=True)
    asset_name = serializers.CharField(source="asset.name", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    critical_process_name = serializers.CharField(source="critical_process.name", read_only=True)
    threat_code = serializers.CharField(source="threat.code", read_only=True)
    threat_title = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()
    treatment_owner_name = serializers.SerializerMethodField()
    assessed_by_name = serializers.SerializerMethodField()
    is_legacy = serializers.SerializerMethodField()
    is_inherited = serializers.SerializerMethodField()
    treatment_rule = serializers.SerializerMethodField()
    can_apply_expected = serializers.SerializerMethodField()
    mitigation_plans_count = serializers.SerializerMethodField()
    mitigation_plans_completed = serializers.SerializerMethodField()
    mitigation_plans_verified = serializers.SerializerMethodField()
    active_acceptance = serializers.SerializerMethodField()

    class Meta:
        model = RiskAssessment
        fields = [
            "id", "plant", "plant_name", "cycle", "evaluated_in_cycle", "is_legacy", "is_inherited",
            "affected_plants", "name", "status",
            "asset_type", "asset", "asset_name", "asset_group_label", "supplier", "supplier_name",
            "threat", "threat_code", "threat_title", "information_classes",
            "critical_process", "critical_process_name", "vulnerability", "consequence",
            "applicable", "not_applicable_reason",
            "probability", "probability_method", "probability_rationale",
            "impact_economic", "impact_legal", "impact_customer", "impact_reputational",
            "impact_people", "impact_operational", "impact", "impact_rationale",
            "matrix_class", "class_override", "override_rationale", "current_class",
            "legal_or_contract_violation",
            "treatment", "treatment_rationale", "treatment_rule",
            "expected_probability", "expected_impact", "expected_class", "can_apply_expected",
            "owner", "owner_name", "treatment_owner", "treatment_owner_external", "treatment_owner_name",
            "plan_due_date",
            "nis2_in_scope", "nis2_art21_category", "impacted_systems",
            "significant_incident_potential", "significant_incident_note",
            "assessed_by", "assessed_by_name", "assessed_at",
            "mitigation_plans_count", "mitigation_plans_completed", "mitigation_plans_verified",
            "active_acceptance", "legacy_snapshot",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_threat_title(self, obj):
        return obj.threat.get_title(_request_lang(self)) if obj.threat else None

    def get_owner_name(self, obj):
        return _user_name(obj.owner)

    def get_assessed_by_name(self, obj):
        return _user_name(obj.assessed_by)

    def get_treatment_owner_name(self, obj):
        from .services import mixed_owner_name

        return mixed_owner_name(obj.treatment_owner, obj.treatment_owner_external)

    def get_is_legacy(self, obj):
        return obj.cycle is not None and obj.cycle.kind == "legacy"

    def get_is_inherited(self, obj):
        return obj.plant_id is None and self.context.get("register_plant") is not None

    def get_treatment_rule(self, obj):
        from .services import treatment_rule

        return treatment_rule(obj.current_class)

    @staticmethod
    def _plans(obj):
        return [p for p in obj.mitigation_plans.all() if p.deleted_at is None]

    def get_can_apply_expected(self, obj):
        plans = self._plans(obj)
        return bool(obj.expected_class and plans and all(p.completed_at and p.verified_at for p in plans))

    def get_mitigation_plans_count(self, obj):
        return len(self._plans(obj))

    def get_mitigation_plans_completed(self, obj):
        return sum(1 for p in self._plans(obj) if p.completed_at)

    def get_mitigation_plans_verified(self, obj):
        return sum(1 for p in self._plans(obj) if p.verified_at)

    def get_active_acceptance(self, obj):
        for acc in obj.acceptances.all():
            if acc.deleted_at is None and acc.status in ("pending", "active"):
                return {"id": str(acc.pk), "status": acc.status, "risk_class": acc.risk_class,
                        "expires_on": acc.expires_on, "upper_opinion": acc.upper_opinion}
        return None


def _score_field():
    return serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=5)


class RiskEvaluationInputSerializer(serializers.Serializer):
    """Tipi dei campi di valutazione; le regole stanno nei service."""

    name = serializers.CharField(required=False, allow_blank=True, max_length=200)
    asset_type = serializers.CharField(required=False, allow_blank=True, max_length=12)
    asset = serializers.PrimaryKeyRelatedField(queryset=Asset.objects.all(), required=False, allow_null=True)
    asset_group_label = serializers.CharField(required=False, allow_blank=True, max_length=200)
    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all(), required=False, allow_null=True)
    threat = serializers.PrimaryKeyRelatedField(queryset=ThreatCatalogEntry.objects.all(), required=False)
    information_classes = serializers.PrimaryKeyRelatedField(
        queryset=InformationClass.objects.all(), many=True, required=False,
    )
    affected_plants = serializers.PrimaryKeyRelatedField(queryset=Plant.objects.all(), many=True, required=False)
    critical_process = serializers.PrimaryKeyRelatedField(
        queryset=CriticalProcess.objects.all(), required=False, allow_null=True,
    )
    vulnerability = serializers.CharField(required=False, allow_blank=True)
    consequence = serializers.CharField(required=False, allow_blank=True)
    probability = _score_field()
    probability_method = serializers.ChoiceField(choices=["", "frequenza", "fer"], required=False)
    probability_rationale = serializers.CharField(required=False, allow_blank=True)
    impact_economic = _score_field()
    impact_legal = _score_field()
    impact_customer = _score_field()
    impact_reputational = _score_field()
    impact_people = _score_field()
    impact_operational = _score_field()
    impact_rationale = serializers.CharField(required=False, allow_blank=True)
    class_override = serializers.IntegerField(required=False, min_value=-1, max_value=1)
    override_rationale = serializers.CharField(required=False, allow_blank=True)
    legal_or_contract_violation = serializers.BooleanField(required=False)
    treatment = serializers.ChoiceField(choices=["", "mitigare", "accettare", "trasferire", "evitare"], required=False)
    treatment_rationale = serializers.CharField(required=False, allow_blank=True)
    expected_probability = _score_field()
    expected_impact = _score_field()
    owner = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True)
    treatment_owner = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True)
    treatment_owner_external = serializers.CharField(required=False, allow_blank=True, max_length=200)
    plan_due_date = serializers.DateField(required=False, allow_null=True)
    nis2_in_scope = serializers.BooleanField(required=False)
    nis2_art21_category = serializers.CharField(required=False, allow_blank=True, max_length=20)
    impacted_systems = serializers.CharField(required=False, allow_blank=True)
    significant_incident_potential = serializers.BooleanField(required=False)
    significant_incident_note = serializers.CharField(required=False, allow_blank=True)


class RiskExistingMeasureSerializer(serializers.ModelSerializer):
    control_title = serializers.SerializerMethodField()

    class Meta:
        model = RiskExistingMeasure
        fields = ["id", "risk", "control_instance", "control_title", "description", "effectiveness", "created_at"]
        read_only_fields = ["id", "created_at", "control_title"]

    def get_control_title(self, obj):
        return _control_label(self, obj.control_instance)


class RiskMitigationPlanSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField(read_only=True)
    verified_by_name = serializers.SerializerMethodField(read_only=True)
    bcp_plan = serializers.PrimaryKeyRelatedField(queryset=BcpPlan.objects.all(), required=False, allow_null=True)
    bcp_plan_title = serializers.CharField(source="bcp_plan.title", read_only=True)
    bcp_plan_status = serializers.CharField(source="bcp_plan.status", read_only=True)
    control_title = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = RiskMitigationPlan
        fields = [
            "id", "assessment", "action", "owner", "owner_external", "owner_name",
            "due_date", "expected_effect", "bcp_plan", "bcp_plan_title", "bcp_plan_status",
            "control_instance", "control_title", "completed_at",
            "verified_at", "verified_by", "verified_by_name", "verification_note",
            "escalation_level", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "created_at", "updated_at", "owner_name", "bcp_plan_title", "bcp_plan_status",
            "control_title", "verified_at", "verified_by", "verified_by_name", "verification_note",
            "escalation_level",
        ]

    def get_owner_name(self, obj):
        from .services import mixed_owner_name

        return mixed_owner_name(obj.owner, obj.owner_external)

    def get_verified_by_name(self, obj):
        return _user_name(obj.verified_by)

    def get_control_title(self, obj):
        return _control_label(self, obj.control_instance)

    def validate(self, attrs):
        from django.utils.translation import gettext as _

        from .services import normalize_mixed_owner

        attrs = normalize_mixed_owner(attrs, "owner", "owner_external")
        risk = attrs.get("assessment") or getattr(self.instance, "assessment", None)
        ci = attrs.get("control_instance")
        if risk is not None and ci is not None and risk.plant_id is not None and ci.plant_id != risk.plant_id:
            raise serializers.ValidationError({"control_instance": _("Il controllo deve essere del sito del registro.")})
        return attrs


class RiskAcceptanceSerializer(serializers.ModelSerializer):
    risk_name = serializers.CharField(source="risk.name", read_only=True)
    plant = serializers.UUIDField(source="risk.plant_id", read_only=True)
    body_name = serializers.CharField(source="body.name", read_only=True)
    opinion_by_name = serializers.SerializerMethodField()
    signatures_display = serializers.SerializerMethodField()
    can_sign = serializers.SerializerMethodField()
    can_give_opinion = serializers.SerializerMethodField()

    class Meta:
        model = RiskAcceptance
        fields = [
            "id", "risk", "risk_name", "plant", "risk_class", "status",
            "required_roles", "signatures_display", "requires_body", "body", "body_name",
            "body_resolution_ref", "rationale", "expires_on",
            "upper_opinion", "opinion_by", "opinion_by_name", "opinion_at", "opinion_note",
            "activated_at", "closed_at", "close_reason", "can_sign", "can_give_opinion",
            "created_at",
        ]
        read_only_fields = fields

    def get_opinion_by_name(self, obj):
        return _user_name(obj.opinion_by)

    def get_signatures_display(self, obj):
        users = {u.pk: u for u in User.objects.filter(pk__in=[s["user_id"] for s in obj.signatures])}
        return [{"role": s["role"], "user": _user_name(users.get(s["user_id"])), "at": s["at"]}
                for s in obj.signatures]

    def _user(self):
        request = self.context.get("request")
        return getattr(request, "user", None)

    def get_can_sign(self, obj):
        from .services import signable_roles

        user = self._user()
        return bool(user and obj.status == "pending" and signable_roles(user, obj))

    def get_can_give_opinion(self, obj):
        from .services import can_give_opinion

        user = self._user()
        return bool(user and obj.status == "pending" and obj.upper_opinion == "pending" and can_give_opinion(user))


class RiskLocalImpactReportSerializer(serializers.ModelSerializer):
    plant_name = serializers.CharField(source="plant.name", read_only=True)
    risk_name = serializers.CharField(source="risk.name", read_only=True)

    class Meta:
        model = RiskLocalImpactReport
        fields = ["id", "risk", "risk_name", "plant", "plant_name", "local_impact", "note", "status",
                  "acknowledged_at", "created_at"]
        read_only_fields = ["id", "status", "acknowledged_at", "created_at", "plant_name", "risk_name"]


# ── Metodologia: catalogo, classi, policy, cicli ─────────────────────────────

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
        if processes and plant is not None and any(p.plant_id != plant.pk for p in processes):
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

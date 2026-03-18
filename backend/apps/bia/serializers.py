from rest_framework import serializers

from .models import CriticalProcess, RiskDecision, TreatmentOption


class CriticalProcessSerializer(serializers.ModelSerializer):
    plant_name = serializers.CharField(source="plant.name", read_only=True)
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    approved_by_username = serializers.CharField(source="approved_by.username", read_only=True)
    validated_by_username = serializers.CharField(source="validated_by.username", read_only=True)
    rto_bcp_status = serializers.CharField(source="rto_bcp_status", read_only=True)

    class Meta:
        model = CriticalProcess
        fields = [
            "id",
            "plant",
            "plant_name",
            "name",
            "owner",
            "owner_username",
            "criticality",
            "status",
            "downtime_cost_hour",
            "fatturato_esposto_anno",
            "danno_reputazionale",
            "danno_normativo",
            "danno_operativo",
            "mtpd_hours",
            "mbco_pct",
            "rto_target_hours",
            "rpo_target_hours",
            "rto_bcp_status",
            "validated_by",
            "validated_by_username",
            "validated_at",
            "approved_by",
            "approved_by_username",
            "approved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "plant_name",
            "owner_username",
            "approved_by_username",
            "validated_by_username",
        ]


class TreatmentOptionSerializer(serializers.ModelSerializer):
    process_name = serializers.CharField(source="process.name", read_only=True)

    class Meta:
        model = TreatmentOption
        fields = [
            "id",
            "process",
            "process_name",
            "title",
            "cost_implementation",
            "cost_annual",
            "ale_reduction_pct",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "process_name"]


class RiskDecisionSerializer(serializers.ModelSerializer):
    process_name = serializers.CharField(source="process.name", read_only=True)
    decided_by_username = serializers.CharField(source="decided_by.username", read_only=True)

    class Meta:
        model = RiskDecision
        fields = [
            "id",
            "process",
            "process_name",
            "decision",
            "rationale",
            "decided_by",
            "decided_by_username",
            "decided_at",
            "review_by",
            "treatment",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "process_name", "decided_by_username", "decided_at"]

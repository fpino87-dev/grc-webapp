from rest_framework import serializers

from .models import CriticalProcess


class CriticalProcessSerializer(serializers.ModelSerializer):
    plant_name = serializers.CharField(source="plant.name", read_only=True)
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    approved_by_username = serializers.CharField(source="approved_by.username", read_only=True)
    validated_by_username = serializers.CharField(source="validated_by.username", read_only=True)
    rto_bcp_status = serializers.CharField(read_only=True)

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

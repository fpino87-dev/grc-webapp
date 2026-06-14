from rest_framework import serializers
from .models import ManagementReview, ReviewAction


class ReviewActionSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()

    def get_owner_name(self, obj):
        if not obj.owner:
            return None
        name = f"{obj.owner.first_name} {obj.owner.last_name}".strip()
        return name or obj.owner.email

    class Meta:
        model = ReviewAction
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "deleted_at"]


class ManagementReviewSerializer(serializers.ModelSerializer):
    actions = ReviewActionSerializer(many=True, read_only=True)
    plant_name = serializers.CharField(source="plant.name", read_only=True, allow_null=True)

    class Meta:
        model = ManagementReview
        fields = "__all__"
        # L'approvazione formale (ISO 27001 §9.3) e lo snapshot dei dati sono
        # governati dalle azioni `approve` / `generate-snapshot` / `complete`
        # (con prerequisiti e audit). Senza questo lock una PATCH potrebbe
        # impostare uno `snapshot_generated_at` fittizio e poi marcare il
        # riesame `approvato` falsificando approvatore e data, scavalcando lo
        # snapshot reale e l'audit. `status` resta editabile (gestito in UI).
        read_only_fields = [
            "id",
            "approval_status",
            "approved_by",
            "approved_at",
            "approval_note",
            "snapshot_generated_at",
            "snapshot_data",
            "kpi_snapshot",
            "created_by",
            "created_at",
            "updated_at",
            "deleted_at",
        ]

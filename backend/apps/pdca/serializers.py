from rest_framework import serializers

from .models import PdcaCycle, PdcaPhase


class PdcaPhaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = PdcaPhase
        fields = ["id", "cycle", "phase", "notes", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class PdcaCycleSerializer(serializers.ModelSerializer):
    phases = PdcaPhaseSerializer(many=True, read_only=True)

    class Meta:
        model = PdcaCycle
        fields = [
            "id",
            "plant",
            "title",
            "trigger_type",
            "trigger_source_id",
            "scope_type",
            "scope_id",
            "fase_corrente",
            "act_description",
            "check_outcome",
            "reopened_as",
            "closed_at",
            "phases",
            "created_at",
            "updated_at",
            "created_by",
        ]
        read_only_fields = [
            "id", "fase_corrente", "reopened_as", "closed_at",
            "created_at", "updated_at", "created_by",
        ]

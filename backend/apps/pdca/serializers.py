from django.conf import settings
from rest_framework import serializers

from .models import PdcaCycle, PdcaPhase


class PdcaPhaseEvidenceSerializer(serializers.Serializer):
    """Rappresentazione compatta dell'evidenza allegata a una fase, con link
    scaricabile per la consultazione in sede di audit."""

    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    evidence_type = serializers.CharField(read_only=True)
    file_url = serializers.SerializerMethodField(read_only=True)

    def get_file_url(self, obj):
        if not obj.file_path:
            return None
        request = self.context.get("request")
        url = f"{settings.MEDIA_URL}{obj.file_path}"
        if request:
            return request.build_absolute_uri(url)
        return url


class PdcaPhaseSerializer(serializers.ModelSerializer):
    evidence = PdcaPhaseEvidenceSerializer(read_only=True)
    outcome_display = serializers.CharField(source="get_outcome_display", read_only=True)
    completed_by_username = serializers.CharField(
        source="completed_by.username", read_only=True, default=None
    )

    class Meta:
        model = PdcaPhase
        fields = [
            "id",
            "cycle",
            "phase",
            "notes",
            "evidence",
            "outcome",
            "outcome_display",
            "completed_at",
            "completed_by",
            "completed_by_username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PdcaCycleSerializer(serializers.ModelSerializer):
    phases = PdcaPhaseSerializer(many=True, read_only=True)

    class Meta:
        model = PdcaCycle
        fields = [
            "id",
            "plant",
            "title",
            "descrizione",
            "trigger_type",
            "trigger_source_id",
            "audit_subtype",
            "riferimento_finding",
            "scope_type",
            "scope_id",
            "fase_corrente",
            "act_description",
            "check_outcome",
            "motivo_archiviazione",
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
            # Campi governati dalle azioni di workflow (advance/close/archivia):
            # non impostabili con una PATCH diretta. Le azioni li scrivono sul
            # modello leggendo il valore dal body della richiesta, non da qui.
            "act_description", "check_outcome", "motivo_archiviazione",
        ]

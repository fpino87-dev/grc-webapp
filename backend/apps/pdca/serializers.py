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
    # Denormalizzati per la lista: evitano una query per riga lato client
    # (il ViewSet fa gia' select_related("plant")).
    plant_name = serializers.CharField(source="plant.name", read_only=True, default=None)
    plant_code = serializers.CharField(source="plant.code", read_only=True, default=None)
    # L'utente corrente può scrivere su questo ciclo? False solo per i cicli
    # di organizzazione visti da chi non ha scope org.
    can_manage = serializers.SerializerMethodField()
    # Finding di audit collegati (prefetch nel viewset): collegamento univoco
    # PDCA ↔ finding ↔ audit (tipo, committente) consultabile da entrambi i lati.
    findings = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = PdcaCycle
        fields = [
            "id",
            "plant",
            "plant_name",
            "plant_code",
            "can_manage",
            "findings",
            "title",
            "descrizione",
            "trigger_type",
            "trigger_source_id",
            "audit_subtype",
            "riferimento_finding",
            "action_owner",
            "target_date",
            "is_overdue",
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
            "id", "plant_name", "plant_code", "can_manage", "findings",
            "fase_corrente", "reopened_as", "closed_at",
            "created_at", "updated_at", "created_by",
            # Campi governati dalle azioni di workflow (advance/close/archivia):
            # non impostabili con una PATCH diretta. Le azioni li scrivono sul
            # modello leggendo il valore dal body della richiesta, non da qui.
            "act_description", "check_outcome", "motivo_archiviazione",
        ]

    def get_findings(self, obj) -> list:
        return [
            {
                "id": str(f.pk),
                "title": f.title,
                "finding_type": f.finding_type,
                "status": f.status,
                "audit_prep": str(f.audit_prep_id),
                "audit_title": f.audit_prep.title,
                # rilievo comune di un audit multi-sito: la UI raggruppa i siti
                "plant_code": f.audit_prep.plant.code,
                "common_key": str(f.common_key) if f.common_key else None,
                "group_title": f.audit_prep.group.title if f.audit_prep.group_id else None,
                "audit_type": f.audit_prep.audit_type,
                "requesting_party": f.audit_prep.requesting_party,
            }
            for f in obj.findings.all()
        ]

    def get_can_manage(self, obj) -> bool:
        return obj.plant_id is not None or bool(self.context.get("can_manage_org"))


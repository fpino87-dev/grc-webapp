from django.conf import settings
from rest_framework import serializers

from .models import Document, DocumentApproval, DocumentVersion, Evidence


class DocumentVersionSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField(read_only=True)
    version_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DocumentVersion
        fields = "__all__"

    def get_version_display(self, obj):
        """Il numero di revisione del documento, se chi ha caricato il file
        l'ha indicato; altrimenti il contatore interno."""
        return obj.version_label or f"v{obj.version_number}"

    def get_file_url(self, obj):
        if not obj.storage_path:
            return None
        request = self.context.get("request")
        url = f"{settings.MEDIA_URL}{obj.storage_path}"
        if request:
            return request.build_absolute_uri(url)
        return url


class DocumentApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentApproval
        fields = "__all__"


class DocumentSerializer(serializers.ModelSerializer):
    latest_version = serializers.SerializerMethodField(read_only=True)
    last_approval = serializers.SerializerMethodField(read_only=True)
    plant_name = serializers.CharField(source="plant.name", read_only=True)
    plant_code = serializers.CharField(source="plant.code", read_only=True)
    shared_plant_names = serializers.SerializerMethodField(read_only=True)
    is_shared_with_current = serializers.SerializerMethodField(read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True, default=None)

    class Meta:
        model = Document
        fields = "__all__"
        # Lo stato del workflow NON si scrive via PATCH: `status`, `approver` e
        # `approved_at` cambiano solo attraverso le azioni submit/approve/reject/
        # archive, che verificano la DocumentWorkflowPolicy e scrivono il record
        # di approvazione + l'audit trail. Senza questo vincolo un utente con
        # semplice permesso di scrittura poteva portare un documento ad
        # "approvato" senza alcuna approvazione tracciata.
        read_only_fields = ["status", "approved_at", "approver"]

    def get_last_approval(self, obj):
        """Ultima approvazione: dice se il documento è in vigore per delibera
        dell'organo e con quali estremi (il verbale è l'evidenza)."""
        records = getattr(obj, "approve_records", None)
        record = records[0] if records else (
            None if records is not None
            else obj.approvals.filter(action="approve").order_by("-created_at").first()
        )
        if record is None:
            return None
        return {
            "mode": record.approval_mode or "in_app",
            "resolution_ref": record.resolution_ref,
            "resolution_date": record.resolution_date,
            "governing_body": record.governing_body.name if record.governing_body_id else None,
            "review_id": str(record.review_id) if record.review_id else None,
            "actor": (
                f"{record.actor.first_name} {record.actor.last_name}".strip() or record.actor.email
            ) if record.actor_id else None,
            "recorded_at": record.created_at,
        }

    def get_latest_version(self, obj):
        version = obj.versions.first()
        if version is None:
            return None
        return DocumentVersionSerializer(version, context=self.context).data

    def get_shared_plant_names(self, obj):
        return [
            {"id": str(p.id), "name": p.name, "code": p.code}
            for p in obj.shared_plants.all()
        ]

    def get_is_shared_with_current(self, obj):
        """True se il documento è visibile al plant corrente tramite condivisione (non è il plant proprietario)."""
        request = self.context.get("request")
        if not request:
            return False
        plant_id = request.query_params.get("plant")
        if not plant_id or not obj.plant_id:
            return False
        return str(obj.plant_id) != plant_id and obj.shared_plants.filter(pk=plant_id).exists()


class EvidenceSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.CharField(source="uploaded_by.username", read_only=True)
    plant_name = serializers.CharField(source="plant.name", read_only=True)
    control_instances_count = serializers.SerializerMethodField(read_only=True)
    linked_controls = serializers.SerializerMethodField(read_only=True)
    file_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Evidence
        fields = [
            "id", "title", "description", "evidence_type",
            "valid_until", "plant", "plant_name",
            "file_path", "file_url", "uploaded_by", "uploaded_by_username",
            "control_instances_count", "linked_controls",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "uploaded_by_username", "plant_name", "file_path", "file_url"]

    def get_control_instances_count(self, obj):
        return obj.control_instances.count()

    def get_linked_controls(self, obj):
        return [
            {
                "id": str(ci.id),
                "control_external_id": ci.control.external_id,
                "control_title": ci.control.get_title(),
                "framework_code": ci.control.framework.code,
            }
            for ci in obj.control_instances.all()
        ]

    def get_file_url(self, obj):
        if not obj.file_path:
            return None
        request = self.context.get("request")
        url = f"{settings.MEDIA_URL}{obj.file_path}"
        if request:
            return request.build_absolute_uri(url)
        return url

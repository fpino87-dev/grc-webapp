from rest_framework import serializers

from .models import Document, DocumentApproval, DocumentVersion, Evidence


class DocumentVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentVersion
        fields = "__all__"


class DocumentApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentApproval
        fields = "__all__"


class DocumentSerializer(serializers.ModelSerializer):
    latest_version = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Document
        fields = "__all__"

    def get_latest_version(self, obj):
        version = obj.versions.first()
        if version is None:
            return None
        return DocumentVersionSerializer(version).data


class EvidenceSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.CharField(source="uploaded_by.username", read_only=True)
    plant_name = serializers.CharField(source="plant.name", read_only=True)
    control_instances_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Evidence
        fields = [
            "id", "title", "description", "evidence_type",
            "valid_until", "plant", "plant_name",
            "file_path", "uploaded_by", "uploaded_by_username",
            "control_instances_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "uploaded_by_username", "plant_name"]

    def get_control_instances_count(self, obj):
        return obj.control_instances.count()

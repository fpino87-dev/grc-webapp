from django.conf import settings
from rest_framework import serializers

from .models import Document, DocumentApproval, DocumentVersion, Evidence


class DocumentVersionSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DocumentVersion
        fields = "__all__"

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

    class Meta:
        model = Document
        fields = "__all__"

    def get_latest_version(self, obj):
        version = obj.versions.first()
        if version is None:
            return None
        return DocumentVersionSerializer(version, context=self.context).data


class EvidenceSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.CharField(source="uploaded_by.username", read_only=True)
    plant_name = serializers.CharField(source="plant.name", read_only=True)
    control_instances_count = serializers.SerializerMethodField(read_only=True)
    file_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Evidence
        fields = [
            "id", "title", "description", "evidence_type",
            "valid_until", "plant", "plant_name",
            "file_path", "file_url", "uploaded_by", "uploaded_by_username",
            "control_instances_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "uploaded_by_username", "plant_name", "file_path", "file_url"]

    def get_control_instances_count(self, obj):
        return obj.control_instances.count()

    def get_file_url(self, obj):
        if not obj.file_path:
            return None
        request = self.context.get("request")
        url = f"{settings.MEDIA_URL}{obj.file_path}"
        if request:
            return request.build_absolute_uri(url)
        return url

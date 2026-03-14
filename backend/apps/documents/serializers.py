from rest_framework import serializers

from .models import Document, DocumentApproval, DocumentVersion


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

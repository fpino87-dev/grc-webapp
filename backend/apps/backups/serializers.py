from rest_framework import serializers

from .models import BackupRecord


class BackupRecordSerializer(serializers.ModelSerializer):
    size_mb = serializers.SerializerMethodField()
    created_by_email = serializers.SerializerMethodField()

    class Meta:
        model = BackupRecord
        fields = [
            "id", "filename", "size_bytes", "size_mb",
            "status", "backup_type", "notes",
            "error_message", "completed_at", "created_at",
            "created_by_email",
        ]

    def get_size_mb(self, obj):
        if obj.size_bytes:
            return round(obj.size_bytes / (1024 * 1024), 2)
        return None

    def get_created_by_email(self, obj):
        if obj.created_by:
            email = obj.created_by.email
            # pseudoanonimizzazione leggera per log UI (non PII completo)
            parts = email.split("@")
            if len(parts) == 2:
                return f"{parts[0][:3]}***@{parts[1]}"
        return None

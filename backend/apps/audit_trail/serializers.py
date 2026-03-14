from rest_framework import serializers

from core.audit import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = "__all__"
        read_only_fields = [
            "id",
            "timestamp_utc",
            "user_id",
            "user_email_at_time",
            "user_role_at_time",
            "action_code",
            "level",
            "entity_type",
            "entity_id",
            "payload",
            "prev_hash",
            "record_hash",
        ]

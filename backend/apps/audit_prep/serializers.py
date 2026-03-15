from rest_framework import serializers
from .models import AuditFinding, AuditPrep, AuditProgram, EvidenceItem


class EvidenceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvidenceItem
        fields = "__all__"


class AuditPrepSerializer(serializers.ModelSerializer):
    evidence_items = EvidenceItemSerializer(many=True, read_only=True)

    class Meta:
        model = AuditPrep
        fields = "__all__"


class AuditFindingSerializer(serializers.ModelSerializer):
    is_overdue = serializers.BooleanField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    closed_by_name = serializers.SerializerMethodField(read_only=True)
    control_external_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AuditFinding
        fields = "__all__"

    def get_closed_by_name(self, obj):
        if not obj.closed_by:
            return None
        u = obj.closed_by
        return f"{u.first_name} {u.last_name}".strip() or u.email

    def get_control_external_id(self, obj):
        if not obj.control_instance:
            return None
        return obj.control_instance.control.external_id


class AuditProgramSerializer(serializers.ModelSerializer):
    completion_pct = serializers.FloatField(read_only=True)
    next_planned_audit = serializers.SerializerMethodField(read_only=True)
    approved_by_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AuditProgram
        fields = "__all__"

    def get_next_planned_audit(self, obj):
        return obj.next_planned_audit

    def get_approved_by_name(self, obj):
        if not obj.approved_by:
            return None
        u = obj.approved_by
        return f"{u.first_name} {u.last_name}".strip() or u.email

from rest_framework import serializers
from .models import AuditFinding, AuditPrep, AuditProgram, EvidenceItem


class EvidenceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvidenceItem
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "deleted_at"]


class AuditPrepSerializer(serializers.ModelSerializer):
    evidence_items = EvidenceItemSerializer(many=True, read_only=True)
    framework_code = serializers.SerializerMethodField()

    class Meta:
        model = AuditPrep
        fields = "__all__"
        # status è governato dalle azioni complete (blocca con Major NC aperti)
        # e annulla; readiness_score è calcolato dall'azione readiness. Una PATCH
        # diretta a "completato" scavalcherebbe il gate sui Major NC.
        read_only_fields = [
            "id", "status", "readiness_score",
            "created_by", "created_at", "updated_at", "deleted_at",
        ]

    def get_framework_code(self, obj):
        return obj.framework.code if obj.framework_id else None


class AuditFindingSerializer(serializers.ModelSerializer):
    is_overdue = serializers.BooleanField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    closed_by_name = serializers.SerializerMethodField(read_only=True)
    control_external_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AuditFinding
        fields = "__all__"
        # La chiusura del finding passa SOLO dall'azione close (close_finding:
        # evidenza, chiusura PDCA, lesson learned, audit). Stato e campi di
        # chiusura non sono impostabili con una PATCH diretta, che marcherebbe
        # un finding "closed" senza evidenza né tracciamento della catena.
        read_only_fields = [
            "id", "status", "closed_at", "closed_by",
            "closure_evidence", "closure_notes", "pdca_cycle", "lesson_learned",
            "auto_generated", "created_by", "created_at", "updated_at", "deleted_at",
        ]

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
    framework_code = serializers.SerializerMethodField()

    class Meta:
        model = AuditProgram
        fields = "__all__"
        # Approvazione (azione approve, audit L1) e piano audit (azioni add-audit
        # /update-audit/launch con whitelist dei campi) sono governati: non
        # impostabili con una PATCH diretta che falsificherebbe l'approvatore o
        # sovrascriverebbe l'intero array planned_audits aggirando la whitelist.
        read_only_fields = [
            "id", "status", "approved_by", "approved_at", "planned_audits",
            "created_by", "created_at", "updated_at", "deleted_at",
        ]

    def get_framework_code(self, obj):
        return obj.framework.code if obj.framework_id else None

    def get_next_planned_audit(self, obj):
        return obj.next_planned_audit

    def get_approved_by_name(self, obj):
        if not obj.approved_by:
            return None
        u = obj.approved_by
        return f"{u.first_name} {u.last_name}".strip() or u.email

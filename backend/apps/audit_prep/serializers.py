from rest_framework import serializers

from apps.plants.models import Plant
from .models import AuditFinding, AuditGroup, AuditPrep, AuditProgram, EvidenceItem


class EvidenceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvidenceItem
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "deleted_at"]


class AuditPrepSerializer(serializers.ModelSerializer):
    evidence_items = EvidenceItemSerializer(many=True, read_only=True)
    framework_code = serializers.SerializerMethodField()
    report_evidence_title = serializers.CharField(
        source="report_evidence.title", read_only=True, default=None,
    )
    report_evidence_filename = serializers.SerializerMethodField()
    # Audit multi-sito: titolo, Scope ID e siti del gruppo (prefetch nel viewset).
    group_title = serializers.CharField(source="group.title", read_only=True, default=None)
    group_scope_id = serializers.CharField(source="group.scope_id", read_only=True, default=None)
    group_sites = serializers.SerializerMethodField()

    class Meta:
        model = AuditPrep
        fields = "__all__"
        # status è governato dalle azioni complete (blocca con Major NC aperti)
        # e annulla; readiness_score è calcolato dall'azione readiness. Una PATCH
        # diretta a "completato" scavalcherebbe il gate sui Major NC.
        # report_evidence si imposta solo con l'azione report-file (upload
        # validato + audit), non collegando un'evidenza qualsiasi via PATCH.
        read_only_fields = [
            "id", "status", "readiness_score", "report_evidence", "group",
            "created_by", "created_at", "updated_at", "deleted_at",
        ]

    def get_framework_code(self, obj):
        return obj.framework.code if obj.framework_id else None

    def get_report_evidence_filename(self, obj):
        import os
        ev = obj.report_evidence
        return os.path.basename(ev.file_path) if ev and ev.file_path else None

    def get_group_sites(self, obj):
        if not obj.group_id:
            return []
        return [
            {"prep": str(p.pk), "plant": str(p.plant_id), "plant_code": p.plant.code}
            for p in sorted(obj.group.preps.all(), key=lambda p: p.plant.code)
        ]


class AuditFindingSerializer(serializers.ModelSerializer):
    is_overdue = serializers.BooleanField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    closed_by_name = serializers.SerializerMethodField(read_only=True)
    control_external_id = serializers.SerializerMethodField(read_only=True)
    # PDCA collegato (select_related nel viewset): titolo e fase per il link.
    pdca_title = serializers.CharField(source="pdca_cycle.title", read_only=True, default=None)
    pdca_phase = serializers.CharField(source="pdca_cycle.fase_corrente", read_only=True, default=None)
    # PDCA di organizzazione (senza sito): copre il rilievo comune su tutti i siti.
    pdca_is_org = serializers.SerializerMethodField(read_only=True)

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
            "auto_generated", "common_key", "created_by", "created_at", "updated_at", "deleted_at",
        ]

    def get_pdca_is_org(self, obj):
        return bool(obj.pdca_cycle_id) and obj.pdca_cycle.plant_id is None

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


class AuditGroupSerializer(serializers.ModelSerializer):
    """Audit comune a più siti. In creazione `plants` (≥ 2) e `coverage_type`
    generano un AuditPrep per sito; in lettura `preps` riepiloga i siti."""
    plants = serializers.PrimaryKeyRelatedField(
        many=True, write_only=True, queryset=Plant.objects.all(),
    )
    coverage_type = serializers.ChoiceField(
        choices=AuditPrep.COVERAGE_CHOICES, write_only=True, required=False, default="campione",
    )
    audit_type = serializers.ChoiceField(choices=AuditPrep.AUDIT_TYPE_CHOICES, required=False, default="interno")
    preps = serializers.SerializerMethodField()
    report_evidence_title = serializers.CharField(source="report_evidence.title", read_only=True, default=None)

    class Meta:
        model = AuditGroup
        fields = [
            "id", "title", "framework", "audit_type", "requesting_party", "auditor_name",
            "audit_date", "scope_id", "report_evidence", "report_evidence_title",
            "plants", "coverage_type", "preps", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "report_evidence", "created_at", "updated_at"]

    def get_preps(self, obj):
        return [
            {"id": str(p.pk), "plant": str(p.plant_id), "plant_code": p.plant.code,
             "status": p.status, "readiness_score": p.readiness_score}
            for p in sorted(obj.preps.all(), key=lambda p: p.plant.code)
        ]

    def validate(self, attrs):
        if self.instance is None and len(attrs.get("plants") or []) < 2:
            from django.utils.translation import gettext as _
            raise serializers.ValidationError({"plants": [_("Un audit multi-sito richiede almeno due siti.")]})
        return attrs


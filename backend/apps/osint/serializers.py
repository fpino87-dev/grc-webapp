"""Serializer DRF per il modulo OSINT."""
from rest_framework import serializers

from .models import (
    OsintAlert,
    OsintEntity,
    OsintFinding,
    OsintScan,
    OsintSettings,
    OsintSubdomain,
)
from .scoring import score_delta


class OsintScanBriefSerializer(serializers.ModelSerializer):
    """Scan minimale per la lista entità."""

    class Meta:
        model = OsintScan
        fields = [
            "id", "scan_date", "status",
            "score_ssl", "score_dns", "score_reputation", "score_grc_context", "score_total",
        ]


class OsintEntityListSerializer(serializers.ModelSerializer):
    last_scan = serializers.SerializerMethodField()
    delta = serializers.SerializerMethodField()
    active_alerts_count = serializers.IntegerField(source="active_alerts_count_cached", read_only=True)

    class Meta:
        model = OsintEntity
        fields = [
            "id", "entity_type", "source_module", "domain", "display_name",
            "is_nis2_critical", "is_active", "scan_frequency",
            "last_scan", "delta", "active_alerts_count",
            "created_at", "updated_at",
        ]

    def _get_prefetched_last_scan(self, obj):
        cached = getattr(obj, "_recent_completed_scans", None)
        if cached is not None:
            return cached[0] if cached else None
        return obj.scans.filter(status="completed").order_by("-scan_date").first()

    def get_last_scan(self, obj):
        scan = self._get_prefetched_last_scan(obj)
        return OsintScanBriefSerializer(scan).data if scan else None

    def get_delta(self, obj):
        # Usa i campi denormalizzati: zero query.
        if obj.last_score_total is None:
            return None
        if obj.prev_score_total is None:
            return 0
        return obj.last_score_total - obj.prev_score_total


class OsintScanDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = OsintScan
        fields = "__all__"


class OsintEntityDetailSerializer(serializers.ModelSerializer):
    last_scan = serializers.SerializerMethodField()
    delta = serializers.SerializerMethodField()
    active_alerts = serializers.SerializerMethodField()
    pending_subdomains_count = serializers.SerializerMethodField()

    class Meta:
        model = OsintEntity
        fields = [
            "id", "entity_type", "source_module", "source_id",
            "domain", "display_name", "is_nis2_critical", "is_active", "scan_frequency",
            "last_scan", "delta", "active_alerts", "pending_subdomains_count",
            "created_at", "updated_at",
        ]

    def get_last_scan(self, obj):
        scan = obj.scans.filter(status="completed").order_by("-scan_date").first()
        return OsintScanDetailSerializer(scan).data if scan else None

    def get_delta(self, obj):
        scan = obj.scans.filter(status="completed").order_by("-scan_date").first()
        return score_delta(obj, scan) if scan else None

    def get_active_alerts(self, obj):
        alerts = obj.alerts.filter(status__in=["new", "acknowledged"]).order_by("-created_at")
        return OsintAlertSerializer(alerts, many=True).data

    def get_pending_subdomains_count(self, obj):
        return obj.subdomains.filter(status="pending").count()


class OsintAlertSerializer(serializers.ModelSerializer):
    entity_domain = serializers.CharField(source="entity.domain", read_only=True)
    entity_display_name = serializers.CharField(source="entity.display_name", read_only=True)

    class Meta:
        model = OsintAlert
        fields = [
            "id", "entity", "entity_domain", "entity_display_name",
            "scan", "alert_type", "severity", "description", "status",
            "linked_incident_id", "linked_task_id",
            "created_at", "resolved_at",
        ]
        read_only_fields = [
            "id", "entity", "scan", "alert_type", "severity", "description",
            "linked_incident_id", "linked_task_id", "created_at",
        ]


class OsintSubdomainSerializer(serializers.ModelSerializer):
    entity_domain = serializers.CharField(source="entity.domain", read_only=True)

    class Meta:
        model = OsintSubdomain
        fields = [
            "id", "entity", "entity_domain", "subdomain", "status",
            "first_seen", "last_seen",
        ]
        read_only_fields = ["id", "entity", "subdomain", "first_seen", "last_seen", "entity_domain"]


class OsintSettingsSerializer(serializers.ModelSerializer):
    # API key: scrittura in chiaro, lettura mascherata
    hibp_api_key = serializers.CharField(write_only=True, allow_blank=True, required=False)
    virustotal_api_key = serializers.CharField(write_only=True, allow_blank=True, required=False)
    abuseipdb_api_key = serializers.CharField(write_only=True, allow_blank=True, required=False)
    gsb_api_key = serializers.CharField(write_only=True, allow_blank=True, required=False)
    otx_api_key = serializers.CharField(write_only=True, allow_blank=True, required=False)

    has_hibp_key = serializers.SerializerMethodField()
    has_virustotal_key = serializers.SerializerMethodField()
    has_abuseipdb_key = serializers.SerializerMethodField()
    has_gsb_key = serializers.SerializerMethodField()
    has_otx_key = serializers.SerializerMethodField()

    class Meta:
        model = OsintSettings
        fields = [
            "id",
            "score_threshold_critical", "score_threshold_warning",
            "freq_my_domains", "freq_suppliers_critical", "freq_suppliers_other",
            "subdomain_auto_include", "anonymization_enabled",
            "hibp_api_key", "virustotal_api_key", "abuseipdb_api_key",
            "gsb_api_key", "otx_api_key",
            "has_hibp_key", "has_virustotal_key", "has_abuseipdb_key",
            "has_gsb_key", "has_otx_key",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]

    def get_has_hibp_key(self, obj): return bool(obj.hibp_api_key)
    def get_has_virustotal_key(self, obj): return bool(obj.virustotal_api_key)
    def get_has_abuseipdb_key(self, obj): return bool(obj.abuseipdb_api_key)
    def get_has_gsb_key(self, obj): return bool(obj.gsb_api_key)
    def get_has_otx_key(self, obj): return bool(obj.otx_api_key)


class OsintFindingSerializer(serializers.ModelSerializer):
    entity_domain = serializers.CharField(source="entity.domain", read_only=True)
    entity_display_name = serializers.CharField(source="entity.display_name", read_only=True)
    entity_type = serializers.CharField(source="entity.entity_type", read_only=True)
    is_nis2_critical = serializers.BooleanField(source="entity.is_nis2_critical", read_only=True)
    playbook = serializers.SerializerMethodField()

    class Meta:
        model = OsintFinding
        fields = [
            "id", "entity", "entity_domain", "entity_display_name", "entity_type",
            "is_nis2_critical",
            "scan", "code", "severity", "params", "status",
            "first_seen", "last_seen", "resolved_at", "resolution_note",
            "accepted_risk_until", "linked_task_id",
            "playbook", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "entity", "scan", "code", "severity", "params",
            "first_seen", "last_seen", "resolved_at",
            "playbook", "created_at", "updated_at",
        ]

    def get_playbook(self, obj):
        from apps.osint.findings import get_playbook
        return get_playbook(obj.code)

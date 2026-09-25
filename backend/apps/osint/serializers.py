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


class _GradeMixin(serializers.Serializer):
    """Voto A–F e punteggio di sicurezza (100 − rischio): più alto = meglio."""
    security = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()

    def _settings(self):
        from apps.osint.models import OsintSettings
        if "osint_settings" not in self.context:
            self.context["osint_settings"] = OsintSettings.load()
        return self.context["osint_settings"]

    def get_security(self, obj):
        from apps.osint.scoring import security_score
        return security_score(obj.last_score_total)

    def get_grade(self, obj):
        from apps.osint.scoring import grade_for
        return grade_for(obj.last_score_total, self._settings())


class OsintEntityListSerializer(_GradeMixin, serializers.ModelSerializer):
    last_scan = serializers.SerializerMethodField()
    delta = serializers.SerializerMethodField()
    active_alerts_count = serializers.IntegerField(source="active_alerts_count_cached", read_only=True)
    # Problemi aperti per gravità (annotati nel queryset) e tendenza (sicurezza)
    open_findings = serializers.SerializerMethodField()
    trend = serializers.SerializerMethodField()

    class Meta:
        model = OsintEntity
        fields = [
            "id", "entity_type", "source_module", "domain", "display_name",
            "is_nis2_critical", "is_active", "scan_frequency",
            "expected_mail", "expected_web",
            "duplicate_candidate_of", "duplicate_verified",
            "last_scan", "delta", "active_alerts_count",
            "security", "grade", "open_findings", "trend",
            "created_at", "updated_at",
        ]

    def get_open_findings(self, obj):
        return {"critical": getattr(obj, "open_critical", 0), "warning": getattr(obj, "open_warning", 0),
                "info": getattr(obj, "open_info", 0)}

    def get_trend(self, obj):
        from apps.osint.scoring import security_score
        scans = getattr(obj, "_recent_completed_scans", None) or []
        return [security_score(s.score_total) for s in reversed(scans[:8]) if s.score_total is not None]

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


class OsintEntityDetailSerializer(_GradeMixin, serializers.ModelSerializer):
    last_scan = serializers.SerializerMethodField()
    delta = serializers.SerializerMethodField()
    active_alerts = serializers.SerializerMethodField()
    pending_subdomains_count = serializers.SerializerMethodField()
    # Problemi dell'entità dal backend (non ricalcolati in interfaccia):
    # aperti + chiusi negli ultimi 90 giorni; eventi = alert recenti.
    findings = serializers.SerializerMethodField()
    events = serializers.SerializerMethodField()

    class Meta:
        model = OsintEntity
        fields = [
            "id", "entity_type", "source_module", "source_id",
            "domain", "display_name", "is_nis2_critical", "is_active", "scan_frequency",
            "expected_mail", "expected_web",
            "duplicate_candidate_of", "duplicate_verified",
            "last_scan", "delta", "active_alerts", "pending_subdomains_count",
            "security", "grade", "findings", "events",
            "created_at", "updated_at",
        ]

    def get_findings(self, obj):
        from datetime import timedelta

        from django.db.models import Q
        from django.utils import timezone

        from apps.osint.findings import OPEN_STATUSES
        recent = timezone.now() - timedelta(days=90)
        qs = obj.findings.filter(deleted_at__isnull=True).filter(
            Q(status__in=OPEN_STATUSES) | Q(resolved_at__gte=recent) | Q(status="accepted_risk")
        ).select_related("entity", "reported_by")
        return OsintFindingSerializer(qs, many=True).data

    def get_events(self, obj):
        alerts = obj.alerts.order_by("-created_at")[:30]
        return OsintAlertSerializer(alerts, many=True).data

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
    abusech_api_key = serializers.CharField(write_only=True, allow_blank=True, required=False)

    has_hibp_key = serializers.SerializerMethodField()
    has_virustotal_key = serializers.SerializerMethodField()
    has_abuseipdb_key = serializers.SerializerMethodField()
    has_gsb_key = serializers.SerializerMethodField()
    has_otx_key = serializers.SerializerMethodField()
    has_abusech_key = serializers.SerializerMethodField()
    enricher_health = serializers.JSONField(read_only=True)

    class Meta:
        model = OsintSettings
        fields = [
            "id",
            "score_threshold_critical", "score_threshold_warning",
            "score_threshold_attention",
            "weight_ssl", "weight_dns", "weight_reputation", "weight_grc",
            "ssl_expiry_warning_days",
            "freq_my_domains", "freq_suppliers_critical", "freq_suppliers_other",
            "subdomain_auto_include", "anonymization_enabled",
            "ct_monitoring_enabled", "ct_lookback_days", "ct_expected_issuers",
            "hibp_api_key", "virustotal_api_key", "abuseipdb_api_key",
            "gsb_api_key", "otx_api_key", "abusech_api_key",
            "has_hibp_key", "has_virustotal_key", "has_abuseipdb_key",
            "has_gsb_key", "has_otx_key", "has_abusech_key",
            "enricher_health",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]

    def validate(self, attrs):
        # I pesi SSL/DNS/Reputazione sono il denominatore per tutte le entità
        # (il GRC vale solo per my_domain): non possono essere tutti e tre a zero,
        # altrimenti lo score sarebbe sempre 0.
        def _w(name):
            return attrs.get(name, getattr(self.instance, name, 0) if self.instance else 0)
        if _w("weight_ssl") + _w("weight_dns") + _w("weight_reputation") == 0:
            raise serializers.ValidationError(
                "Almeno uno tra i pesi SSL, DNS e Reputazione deve essere maggiore di zero."
            )
        return attrs

    def get_has_hibp_key(self, obj): return bool(obj.hibp_api_key)
    def get_has_virustotal_key(self, obj): return bool(obj.virustotal_api_key)
    def get_has_abuseipdb_key(self, obj): return bool(obj.abuseipdb_api_key)
    def get_has_gsb_key(self, obj): return bool(obj.gsb_api_key)
    def get_has_otx_key(self, obj): return bool(obj.otx_api_key)
    def get_has_abusech_key(self, obj): return bool(obj.abusech_api_key)


class OsintFindingSerializer(serializers.ModelSerializer):
    entity_domain = serializers.CharField(source="entity.domain", read_only=True)
    entity_display_name = serializers.CharField(source="entity.display_name", read_only=True)
    entity_type = serializers.CharField(source="entity.entity_type", read_only=True)
    is_nis2_critical = serializers.BooleanField(source="entity.is_nis2_critical", read_only=True)
    playbook = serializers.SerializerMethodField()
    reported_by_name = serializers.SerializerMethodField()
    report_overdue = serializers.SerializerMethodField()

    class Meta:
        model = OsintFinding
        fields = [
            "id", "entity", "entity_domain", "entity_display_name", "entity_type",
            "is_nis2_critical",
            "scan", "code", "severity", "params", "status",
            "first_seen", "last_seen", "resolved_at", "resolution_note",
            "accepted_risk_until", "linked_task_id",
            "reported_at", "reported_by_name", "report_note", "report_overdue",
            "playbook", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "entity", "scan", "code", "severity", "params",
            "first_seen", "last_seen", "resolved_at",
            "reported_at", "reported_by_name", "report_note", "report_overdue",
            "playbook", "created_at", "updated_at",
        ]

    def get_playbook(self, obj):
        from apps.osint.findings import get_playbook
        return get_playbook(obj.code)

    def get_reported_by_name(self, obj):
        u = obj.reported_by
        return (f"{u.first_name} {u.last_name}".strip() or u.username) if u else None

    def get_report_overdue(self, obj):
        from apps.osint.findings import report_overdue
        return report_overdue(obj)


class OsintPostureSerializer(serializers.ModelSerializer):
    """
    Postura attesa: l'unica cosa dell'entità che NON deriva dal modulo di
    origine, e quindi l'unica scrivibile qui. Tutto il resto (dominio, nome,
    criticità NIS2) è specchio della sorgente e si modifica là.
    """

    class Meta:
        model = OsintEntity
        fields = ["expected_mail", "expected_web"]

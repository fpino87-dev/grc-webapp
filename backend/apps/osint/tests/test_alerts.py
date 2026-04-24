"""Test Step 5 — Alert engine OSINT."""
import pytest
from unittest.mock import patch, MagicMock

from apps.osint.models import (
    AlertStatus, AlertType, AlertSeverity,
    EntityType, OsintAlert, OsintEntity, OsintScan, OsintSettings,
    ScanStatus, SourceModule,
)
from apps.osint.alerts import run_alerts, _has_active_alert
from apps.plants.models import Plant


pytestmark = pytest.mark.django_db


def _make_plant():
    return Plant.objects.create(
        code="ALP1", name="Alert Plant", country="IT",
        nis2_scope="essenziale", status="attivo",
    )


def _make_entity(plant, entity_type=EntityType.MY_DOMAIN, source_module=SourceModule.SITES):
    return OsintEntity.objects.create(
        entity_type=entity_type,
        source_module=source_module,
        source_id=plant.id,
        domain="test.example.com",
        display_name="Test Entity",
        is_nis2_critical=True,
    )


def _make_scan(entity, **kwargs):
    return OsintScan.objects.create(
        entity=entity,
        status=ScanStatus.COMPLETED,
        ssl_valid=kwargs.get("ssl_valid", True),
        ssl_days_remaining=kwargs.get("ssl_days_remaining", 120),
        ssl_expiry_date=kwargs.get("ssl_expiry_date", None),
        spf_present=kwargs.get("spf_present", True),
        dmarc_present=kwargs.get("dmarc_present", True),
        dmarc_policy=kwargs.get("dmarc_policy", "reject"),
        mx_present=kwargs.get("mx_present", True),
        gsb_status=kwargs.get("gsb_status", "safe"),
        in_blacklist=kwargs.get("in_blacklist", False),
        blacklist_sources=kwargs.get("blacklist_sources", []),
        vt_malicious=kwargs.get("vt_malicious", 0),
        abuseipdb_score=kwargs.get("abuseipdb_score", 0),
        otx_pulses=kwargs.get("otx_pulses", 0),
        hibp_breaches=kwargs.get("hibp_breaches", 0),
        score_total=kwargs.get("score_total", 10),
    )


class TestTriggerScoreCritical:
    def test_no_alert_below_threshold(self):
        s = OsintSettings.load()
        p = _make_plant()
        entity = _make_entity(p)
        scan = _make_scan(entity, score_total=50)
        alerts = run_alerts(entity, scan, s)
        types = [a.alert_type for a in alerts]
        assert AlertType.SCORE_CRITICAL not in types

    def test_creates_alert_first_time_critical(self):
        s = OsintSettings.load()
        p = _make_plant()
        entity = _make_entity(p)
        scan = _make_scan(entity, score_total=80)
        alerts = run_alerts(entity, scan, s)
        types = [a.alert_type for a in alerts]
        assert AlertType.SCORE_CRITICAL in types

    def test_no_duplicate_if_already_active(self):
        s = OsintSettings.load()
        p = _make_plant()
        entity = _make_entity(p)
        scan = _make_scan(entity, score_total=80)
        run_alerts(entity, scan, s)
        scan2 = _make_scan(entity, score_total=85)
        alerts2 = run_alerts(entity, scan2, s)
        types = [a.alert_type for a in alerts2]
        assert AlertType.SCORE_CRITICAL not in types


class TestTriggerSSL:
    def test_ssl_expired_creates_critical(self):
        s = OsintSettings.load()
        p = _make_plant()
        entity = _make_entity(p)
        scan = _make_scan(entity, ssl_valid=False, ssl_days_remaining=None, score_total=10)
        alerts = run_alerts(entity, scan, s)
        ssl_alerts = [a for a in alerts if a.alert_type == AlertType.SSL_EXPIRED]
        assert len(ssl_alerts) == 1
        assert ssl_alerts[0].severity == AlertSeverity.CRITICAL

    def test_ssl_expiry_warning_30_days(self):
        s = OsintSettings.load()
        p = _make_plant()
        entity = _make_entity(p)
        scan = _make_scan(entity, ssl_valid=True, ssl_days_remaining=20, score_total=10)
        alerts = run_alerts(entity, scan, s)
        ssl_alerts = [a for a in alerts if a.alert_type == AlertType.SSL_EXPIRY]
        assert len(ssl_alerts) == 1
        assert ssl_alerts[0].severity == AlertSeverity.WARNING

    def test_no_ssl_alert_ok(self):
        s = OsintSettings.load()
        p = _make_plant()
        entity = _make_entity(p)
        scan = _make_scan(entity, ssl_valid=True, ssl_days_remaining=200, score_total=10)
        alerts = run_alerts(entity, scan, s)
        types = [a.alert_type for a in alerts]
        assert AlertType.SSL_EXPIRY not in types
        assert AlertType.SSL_EXPIRED not in types


class TestTriggerDMARC:
    def test_dmarc_missing_creates_warning(self):
        s = OsintSettings.load()
        p = _make_plant()
        entity = _make_entity(p)
        scan = _make_scan(entity, dmarc_present=False, score_total=10)
        alerts = run_alerts(entity, scan, s)
        dmarc_alerts = [a for a in alerts if a.alert_type == AlertType.DMARC_MISSING]
        assert len(dmarc_alerts) == 1
        assert dmarc_alerts[0].severity == AlertSeverity.WARNING

    def test_no_duplicate_dmarc(self):
        s = OsintSettings.load()
        p = _make_plant()
        entity = _make_entity(p)
        scan1 = _make_scan(entity, dmarc_present=False, score_total=10)
        run_alerts(entity, scan1, s)
        scan2 = _make_scan(entity, dmarc_present=False, score_total=10)
        alerts2 = run_alerts(entity, scan2, s)
        types = [a.alert_type for a in alerts2]
        assert AlertType.DMARC_MISSING not in types


class TestTriggerBlacklist:
    def test_new_blacklist_creates_critical(self):
        s = OsintSettings.load()
        p = _make_plant()
        entity = _make_entity(p)
        scan = _make_scan(entity, in_blacklist=True, blacklist_sources=["spamhaus"], score_total=20)
        alerts = run_alerts(entity, scan, s)
        bl = [a for a in alerts if a.alert_type == AlertType.BLACKLIST_NEW]
        assert len(bl) == 1
        assert bl[0].severity == AlertSeverity.CRITICAL

    def test_existing_blacklist_no_new_alert(self):
        s = OsintSettings.load()
        p = _make_plant()
        entity = _make_entity(p)
        prev = _make_scan(entity, in_blacklist=True, score_total=20)
        scan = _make_scan(entity, in_blacklist=True, score_total=20)
        alerts = run_alerts(entity, scan, s)
        bl = [a for a in alerts if a.alert_type == AlertType.BLACKLIST_NEW]
        assert len(bl) == 0


class TestRoutingIncidentTask:
    def test_critical_my_domain_creates_incident(self):
        s = OsintSettings.load()
        p = _make_plant()
        entity = _make_entity(p, EntityType.MY_DOMAIN)
        scan = _make_scan(entity, ssl_valid=False, ssl_days_remaining=None, score_total=10)
        from apps.incidents.models import Incident
        before = Incident.objects.count()
        run_alerts(entity, scan, s)
        assert Incident.objects.count() > before

    def test_critical_supplier_creates_task(self):
        s = OsintSettings.load()
        p = _make_plant()
        entity = _make_entity(p, EntityType.SUPPLIER, SourceModule.SUPPLIERS)
        scan = _make_scan(entity, ssl_valid=False, ssl_days_remaining=None, score_total=10)
        from apps.tasks.models import Task
        before = Task.objects.count()
        run_alerts(entity, scan, s)
        assert Task.objects.count() > before

    def test_new_subdomain_no_incident_or_task(self):
        from apps.osint.models import OsintSubdomain
        s = OsintSettings.load()
        p = _make_plant()
        entity = _make_entity(p, EntityType.MY_DOMAIN)
        OsintSubdomain.objects.create(entity=entity, subdomain="sub.test.example.com")
        scan = _make_scan(entity, score_total=10)
        from apps.incidents.models import Incident
        from apps.tasks.models import Task
        inc_before = Incident.objects.count()
        task_before = Task.objects.count()
        alerts = run_alerts(entity, scan, s)
        sub_alerts = [a for a in alerts if a.alert_type == AlertType.NEW_SUBDOMAIN]
        assert len(sub_alerts) == 1
        assert Incident.objects.count() == inc_before
        assert Task.objects.count() == task_before

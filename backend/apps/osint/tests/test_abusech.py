"""Test P2-3 — enricher abuse.ch (ThreatFox + URLhaus).

Tutte le chiamate di rete sono mockate: i test non toccano abuse.ch.
"""
import pytest
from unittest.mock import patch

from apps.osint.enrichers import abusech
from apps.osint.enrichers.abusech import THREATFOX_URL, URLHAUS_HOST_URL
from apps.osint.scoring import _score_reputation
from apps.osint.findings import _detect_finding_codes, _severity_for
from apps.osint.alerts import run_alerts
from apps.osint.models import (
    AlertSeverity, AlertType, EntityType, FindingCode, OsintEntity, OsintScan,
    OsintSettings, ScanStatus, SourceModule,
)
from apps.plants.models import Plant


pytestmark = pytest.mark.django_db


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _entity(domain="example.com", etype=EntityType.MY_DOMAIN):
    p = Plant.objects.create(code="AB1", name="AbusePlant", country="IT",
                             nis2_scope="essenziale", status="attivo")
    return OsintEntity.objects.create(
        entity_type=etype, source_module=SourceModule.SITES,
        source_id=p.id, domain=domain, display_name="Example",
    )


def _settings_with_key():
    s = OsintSettings.load()
    s.abusech_api_key = "test-auth-key"
    return s


# ---------------------------------------------------------------------------
# Enricher: pattern keyed
# ---------------------------------------------------------------------------

class TestEnricherKeyed:
    def test_noop_without_key(self):
        s = OsintSettings.load()
        s.abusech_api_key = ""
        scan = OsintScan()
        with patch.object(abusech, "requests") as mock_req:
            assert abusech.run(_entity(), scan, s) is True
            mock_req.post.assert_not_called()
        assert scan.threatfox_iocs is None
        assert scan.urlhaus_urls is None

    def test_skips_non_public_target(self):
        s = _settings_with_key()
        scan = OsintScan()
        with patch("apps.osint.validators.is_public_internet_target", return_value=False), \
             patch.object(abusech, "requests") as mock_req:
            assert abusech.run(_entity(domain="db.internal"), scan, s) is False
            mock_req.post.assert_not_called()
        assert scan.enricher_errors.get("abusech") == "non_public_target"


# ---------------------------------------------------------------------------
# Enricher: parsing risposte mockate
# ---------------------------------------------------------------------------

class TestEnricherParsing:
    def _dispatch(self, threatfox_payload, urlhaus_payload):
        def _post(url, **kwargs):
            if url == THREATFOX_URL:
                return _FakeResp(threatfox_payload)
            if url == URLHAUS_HOST_URL:
                return _FakeResp(urlhaus_payload)
            raise AssertionError(f"unexpected url {url}")
        return _post

    def test_threatfox_and_urlhaus_match(self):
        s = _settings_with_key()
        scan = OsintScan()
        tf = {"query_status": "ok", "data": [
            {"id": 1, "ioc": "example.com", "malware_printable": "Cobalt Strike"},
            {"id": 2, "ioc": "example.com", "malware_printable": "Emotet"},
        ]}
        uh = {"query_status": "ok", "urls": [{"url": "http://example.com/x"}]}
        with patch("apps.osint.validators.is_public_internet_target", return_value=True), \
             patch("apps.osint.validators.safe_resolve_public_ip", return_value=None), \
             patch.object(abusech.requests, "post", side_effect=self._dispatch(tf, uh)):
            assert abusech.run(_entity(), scan, s) is True
        assert scan.threatfox_iocs == 2
        assert set(scan.threatfox_malware) == {"Cobalt Strike", "Emotet"}
        assert scan.urlhaus_urls == 1

    def test_dedup_domain_and_ip(self):
        # Stesso IoC id restituito sia per il dominio sia per l'IP → contato una volta.
        s = _settings_with_key()
        scan = OsintScan()
        tf = {"query_status": "ok", "data": [{"id": 7, "malware": "njRAT"}]}
        uh = {"query_status": "no_results"}
        with patch("apps.osint.validators.is_public_internet_target", return_value=True), \
             patch("apps.osint.validators.safe_resolve_public_ip", return_value="203.0.113.10"), \
             patch.object(abusech.requests, "post", side_effect=self._dispatch(tf, uh)):
            abusech.run(_entity(), scan, s)
        assert scan.threatfox_iocs == 1
        assert scan.threatfox_malware == ["njRAT"]
        assert scan.urlhaus_urls == 0

    def test_clean_target(self):
        s = _settings_with_key()
        scan = OsintScan()
        tf = {"query_status": "no_result"}
        uh = {"query_status": "no_results"}
        with patch("apps.osint.validators.is_public_internet_target", return_value=True), \
             patch("apps.osint.validators.safe_resolve_public_ip", return_value=None), \
             patch.object(abusech.requests, "post", side_effect=self._dispatch(tf, uh)):
            abusech.run(_entity(), scan, s)
        assert scan.threatfox_iocs == 0
        assert scan.threatfox_malware == []
        assert scan.urlhaus_urls == 0


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

class TestScoring:
    def test_threatfox_bumps_reputation(self):
        clean = OsintScan(gsb_status="safe")
        listed = OsintScan(gsb_status="safe", threatfox_iocs=1)
        assert _score_reputation(listed) >= _score_reputation(clean) + 50

    def test_urlhaus_bumps_reputation(self):
        clean = OsintScan(gsb_status="safe")
        listed = OsintScan(gsb_status="safe", urlhaus_urls=2)
        assert _score_reputation(listed) >= _score_reputation(clean) + 40

    def test_none_does_not_penalize(self):
        scan = OsintScan(gsb_status="safe")  # threatfox/urlhaus = None
        assert _score_reputation(scan) == 0


# ---------------------------------------------------------------------------
# Finding + alert engine
# ---------------------------------------------------------------------------

class TestFindingAlert:
    def _scan(self, entity):
        return OsintScan.objects.create(
            entity=entity, status=ScanStatus.COMPLETED,
            ssl_valid=True, ssl_days_remaining=120,
            spf_present=True, dmarc_present=True, dmarc_policy="reject", mx_present=True,
            gsb_status="safe", in_blacklist=False, score_total=90,
            threatfox_iocs=3, threatfox_malware=["Cobalt Strike"],
            urlhaus_urls=2,
        )

    def test_findings_detected_critical(self):
        entity = _entity()
        scan = self._scan(entity)
        detected = _detect_finding_codes(entity, scan)
        assert FindingCode.THREATFOX_LISTED in detected
        assert FindingCode.URLHAUS_LISTED in detected
        assert detected[FindingCode.THREATFOX_LISTED]["count"] == 3
        assert _severity_for(FindingCode.THREATFOX_LISTED) == AlertSeverity.CRITICAL
        assert _severity_for(FindingCode.URLHAUS_LISTED) == AlertSeverity.CRITICAL

    def test_alerts_created_critical(self):
        s = OsintSettings.load()
        entity = _entity()
        scan = self._scan(entity)
        alerts = run_alerts(entity, scan, s)
        types = {a.alert_type for a in alerts}
        assert AlertType.THREATFOX_LISTED in types
        assert AlertType.URLHAUS_LISTED in types
        for a in alerts:
            if a.alert_type in (AlertType.THREATFOX_LISTED, AlertType.URLHAUS_LISTED):
                assert a.severity == AlertSeverity.CRITICAL

    def test_no_alert_when_clean(self):
        s = OsintSettings.load()
        entity = _entity()
        scan = OsintScan.objects.create(
            entity=entity, status=ScanStatus.COMPLETED,
            ssl_valid=True, ssl_days_remaining=120,
            spf_present=True, dmarc_present=True, dmarc_policy="reject", mx_present=True,
            gsb_status="safe", in_blacklist=False, score_total=10,
            threatfox_iocs=0, urlhaus_urls=0,
        )
        alerts = run_alerts(entity, scan, s)
        types = {a.alert_type for a in alerts}
        assert AlertType.THREATFOX_LISTED not in types
        assert AlertType.URLHAUS_LISTED not in types

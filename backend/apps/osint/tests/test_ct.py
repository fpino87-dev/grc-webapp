"""Test P2-3 — Certificate Transparency monitoring (crt.sh)."""
import pytest
from datetime import datetime, timedelta, timezone as tz

from apps.osint.enrichers.ct import _parse_dt, _names_from_entry, analyze_ct
from apps.osint.findings import _detect_finding_codes, _severity_for
from apps.osint.alerts import run_alerts
from apps.osint.models import (
    AlertSeverity, AlertType, EntityType, FindingCode, OsintEntity, OsintScan,
    OsintSettings, ScanStatus, SourceModule,
)
from apps.plants.models import Plant


pytestmark = pytest.mark.django_db


def _recent_iso(days_ago: int) -> str:
    return (datetime.now(tz=tz.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%S")


def _entry(issuer, names, days_ago):
    return {
        "id": 12345,
        "issuer_name": issuer,
        "name_value": "\n".join(names),
        "not_before": _recent_iso(days_ago),
        "entry_timestamp": _recent_iso(days_ago),
    }


# ---------------------------------------------------------------------------
# Parser helpers
# ---------------------------------------------------------------------------

class TestParseDt:
    def test_plain(self):
        assert _parse_dt("2026-01-15T12:00:00") is not None

    def test_with_z(self):
        assert _parse_dt("2026-01-15T12:00:00Z") is not None

    def test_microseconds(self):
        assert _parse_dt("2026-01-15T12:00:00.123456") is not None

    def test_invalid(self):
        assert _parse_dt("not-a-date") is None
        assert _parse_dt(None) is None


class TestNames:
    def test_filters_to_domain(self):
        names = _names_from_entry("a.example.com\nevil.com\n*.example.com", "example.com")
        assert "a.example.com" in names
        assert "*.example.com" in names
        assert "evil.com" not in names


# ---------------------------------------------------------------------------
# analyze_ct
# ---------------------------------------------------------------------------

def _entity():
    p = Plant.objects.create(code="CT1", name="CtPlant", country="IT",
                             nis2_scope="essenziale", status="attivo")
    return OsintEntity.objects.create(
        entity_type=EntityType.MY_DOMAIN, source_module=SourceModule.SITES,
        source_id=p.id, domain="example.com", display_name="Example",
    )


class TestAnalyzeCt:
    def test_recent_window_filters_old(self):
        s = OsintSettings.load()
        s.ct_lookback_days = 30
        s.ct_expected_issuers = []
        scan = OsintScan()
        entries = [
            _entry("C=US, O=Let's Encrypt, CN=R3", ["a.example.com"], days_ago=5),
            _entry("C=US, O=Let's Encrypt, CN=R3", ["old.example.com"], days_ago=200),
        ]
        analyze_ct(_entity(), scan, entries, s)
        assert len(scan.ct_recent_certs) == 1
        assert scan.ct_recent_certs[0]["names"] == ["a.example.com"]
        assert scan.ct_unexpected_issuers == []  # nessuna allowlist → nessun inatteso

    def test_unexpected_issuer_with_allowlist(self):
        s = OsintSettings.load()
        s.ct_lookback_days = 30
        s.ct_expected_issuers = ["Let's Encrypt", "DigiCert"]
        scan = OsintScan()
        entries = [
            _entry("C=US, O=Let's Encrypt, CN=R3", ["a.example.com"], days_ago=2),
            _entry("C=CN, O=Rogue CA Ltd, CN=evil", ["vpn.example.com"], days_ago=3),
        ]
        analyze_ct(_entity(), scan, entries, s)
        assert len(scan.ct_recent_certs) == 2
        assert any("Rogue CA" in i for i in scan.ct_unexpected_issuers)
        assert not any("Let's Encrypt" in i for i in scan.ct_unexpected_issuers)

    def test_unexpected_issuer_ignored_when_no_domain_names(self):
        # Entry recente da CA fuori allowlist ma SENZA nomi pertinenti al dominio
        # → non deve generare un issuer inatteso (niente alert CRITICAL spurio).
        s = OsintSettings.load()
        s.ct_lookback_days = 30
        s.ct_expected_issuers = ["Let's Encrypt"]
        scan = OsintScan()
        entries = [_entry("C=CN, O=Rogue CA Ltd", ["unrelated.other.com"], days_ago=2)]
        analyze_ct(_entity(), scan, entries, s)
        assert scan.ct_recent_certs == []  # nessun nome del dominio → non recente-rilevante
        assert scan.ct_unexpected_issuers == []

    def test_disabled_is_noop(self):
        s = OsintSettings.load()
        s.ct_monitoring_enabled = False
        scan = OsintScan()
        analyze_ct(_entity(), scan, [_entry("O=Whatever", ["a.example.com"], 1)], s)
        assert scan.ct_recent_certs == []
        assert scan.ct_unexpected_issuers == []


# ---------------------------------------------------------------------------
# Findings + alert
# ---------------------------------------------------------------------------

class TestCtFindingAlert:
    def _scan_with_unexpected(self, entity):
        return OsintScan.objects.create(
            entity=entity, status=ScanStatus.COMPLETED,
            ssl_valid=True, ssl_days_remaining=120,
            spf_present=True, dmarc_present=True, dmarc_policy="reject", mx_present=True,
            gsb_status="safe", in_blacklist=False, score_total=10,
            ct_unexpected_issuers=["C=CN, O=Rogue CA Ltd"],
            ct_recent_certs=[{"id": 1, "issuer": "C=CN, O=Rogue CA Ltd", "names": ["vpn.example.com"]}],
        )

    def test_finding_detected_critical(self):
        entity = _entity()
        scan = self._scan_with_unexpected(entity)
        detected = _detect_finding_codes(entity, scan)
        assert FindingCode.CT_UNEXPECTED_ISSUER in detected
        assert _severity_for(FindingCode.CT_UNEXPECTED_ISSUER) == AlertSeverity.CRITICAL

    def test_alert_created_critical(self):
        s = OsintSettings.load()
        entity = _entity()
        scan = self._scan_with_unexpected(entity)
        alerts = run_alerts(entity, scan, s)
        ct_alerts = [a for a in alerts if a.alert_type == AlertType.CT_UNEXPECTED_ISSUER]
        assert len(ct_alerts) == 1
        assert ct_alerts[0].severity == AlertSeverity.CRITICAL

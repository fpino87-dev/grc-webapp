"""Test per la "weaponization" dei domini lookalike.

Verifica che la severity del finding LOOKALIKE sia dinamica:
- almeno un sosia con MX (armato per phishing email) → CRITICAL
- sosia solo attivi (A record, niente MX) → WARNING
e che l'enricher dnstwist marchi il flag `mx` sui risultati.
"""
from unittest.mock import patch

import pytest


def _make_entity(**kw):
    from apps.osint.models import OsintEntity, EntityType, SourceModule
    defaults = dict(
        entity_type=EntityType.MY_DOMAIN,
        source_module=SourceModule.SITES,
        source_id="00000000-0000-0000-0000-0000000000bb",
        domain="acme.example.com",
        display_name="Acme",
    )
    defaults.update(kw)
    return OsintEntity.objects.create(**defaults)


# ── severity dinamica ───────────────────────────────────────────────────────

def test_lookalike_severity_critical_when_armed():
    from apps.osint.findings import _severity_for
    from apps.osint.models import FindingCode, AlertSeverity
    params = {"domains": [
        {"domain": "acrne.example.com", "ips": ["1.2.3.4"], "mx": False},
        {"domain": "acme-login.com", "ips": ["5.6.7.8"], "mx": True},
    ]}
    assert _severity_for(FindingCode.LOOKALIKE, params) == AlertSeverity.CRITICAL


def test_lookalike_severity_warning_when_only_active():
    from apps.osint.findings import _severity_for
    from apps.osint.models import FindingCode, AlertSeverity
    params = {"domains": [
        {"domain": "acrne.example.com", "ips": ["1.2.3.4"], "mx": False},
    ]}
    assert _severity_for(FindingCode.LOOKALIKE, params) == AlertSeverity.WARNING


def test_lookalike_severity_warning_when_no_params():
    from apps.osint.findings import _severity_for
    from apps.osint.models import FindingCode, AlertSeverity
    assert _severity_for(FindingCode.LOOKALIKE, None) == AlertSeverity.WARNING


# ── finding creato con la severity corretta ─────────────────────────────────

@pytest.mark.django_db
def test_lookalike_finding_critical_for_armed_domain():
    from apps.osint.models import OsintScan, FindingCode, OsintFinding, AlertSeverity
    from apps.osint.findings import sync_findings

    entity = _make_entity()
    scan = OsintScan.objects.create(
        entity=entity,
        ssl_valid=True,
        lookalike_domains=[{"domain": "acme-login.com", "ips": ["5.6.7.8"], "mx": True}],
    )
    sync_findings(entity, scan)
    finding = OsintFinding.objects.get(entity=entity, code=FindingCode.LOOKALIKE)
    assert finding.severity == AlertSeverity.CRITICAL


@pytest.mark.django_db
def test_lookalike_finding_severity_escalates_across_scans():
    """Un sosia che inizia parcheggiato (WARNING) e poi configura MX → CRITICAL."""
    from apps.osint.models import OsintScan, FindingCode, OsintFinding, AlertSeverity
    from apps.osint.findings import sync_findings

    entity = _make_entity()
    scan1 = OsintScan.objects.create(
        entity=entity, ssl_valid=True,
        lookalike_domains=[{"domain": "acme-login.com", "ips": ["5.6.7.8"], "mx": False}],
    )
    sync_findings(entity, scan1)
    f = OsintFinding.objects.get(entity=entity, code=FindingCode.LOOKALIKE)
    assert f.severity == AlertSeverity.WARNING

    scan2 = OsintScan.objects.create(
        entity=entity, ssl_valid=True,
        lookalike_domains=[{"domain": "acme-login.com", "ips": ["5.6.7.8"], "mx": True}],
    )
    sync_findings(entity, scan2)
    f.refresh_from_db()
    assert f.severity == AlertSeverity.CRITICAL


# ── enricher: flag mx popolato ──────────────────────────────────────────────

def test_has_mx_helper():
    from apps.osint.enrichers.dnstwist import _has_mx

    class FakeAns(list):
        pass

    with patch("dns.resolver.Resolver") as MockResolver:
        MockResolver.return_value.resolve.return_value = FakeAns(["mx.acme-login.com"])
        assert _has_mx("acme-login.com") is True

    with patch("dns.resolver.Resolver") as MockResolver:
        MockResolver.return_value.resolve.side_effect = Exception("nxdomain")
        assert _has_mx("nope.example.com") is False

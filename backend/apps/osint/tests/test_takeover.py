"""Test per il rilevamento subdomain takeover (enricher + finding + alert).

DNS-only: tutti i lookup CNAME/A sono mockati per non dipendere dalla rete e per
non incappare nel validatore anti-SSRF.
"""
from unittest.mock import patch

import pytest


def _make_entity(**kw):
    from apps.osint.models import OsintEntity, EntityType, SourceModule
    defaults = dict(
        entity_type=EntityType.MY_DOMAIN,
        source_module=SourceModule.SITES,
        source_id="00000000-0000-0000-0000-0000000000aa",
        domain="acme.example.com",
        display_name="Acme",
    )
    defaults.update(kw)
    return OsintEntity.objects.create(**defaults)


# ── _match_service: fingerprint dei servizi cloud ───────────────────────────

def test_match_service_known_and_unknown():
    from apps.osint.enrichers.takeover import _match_service
    assert _match_service("acme-bucket.s3.amazonaws.com") == "AWS S3"
    assert _match_service("acme.github.io") == "GitHub Pages"
    assert _match_service("acme.herokuapp.com") == "Heroku"
    assert _match_service("acme.azurewebsites.net") == "Azure"
    # Target legittimo / non in fingerprint → nessun servizio
    assert _match_service("acme.example.com") is None
    assert _match_service("www.google.com") is None


# ── enricher: CNAME dangling (NXDOMAIN) genera un candidato ─────────────────

@pytest.mark.django_db
def test_takeover_detects_dangling_cname():
    from apps.osint.models import OsintScan, OsintSubdomain, SubdomainStatus, OsintSettings
    from apps.osint.enrichers import takeover

    entity = _make_entity()
    OsintSubdomain.objects.create(entity=entity, subdomain="shop.acme.example.com", status=SubdomainStatus.INCLUDED)
    scan = OsintScan.objects.create(entity=entity)

    with patch("apps.osint.enrichers.takeover._cname_target", return_value="acme-bucket.s3.amazonaws.com"), \
         patch("apps.osint.enrichers.takeover._target_resolves", return_value=False):
        ok = takeover.run(entity, scan, OsintSettings.load())

    assert ok is True
    assert len(scan.takeover_candidates) == 1
    cand = scan.takeover_candidates[0]
    assert cand["subdomain"] == "shop.acme.example.com"
    assert cand["service"] == "AWS S3"


@pytest.mark.django_db
def test_takeover_ignores_resolving_target():
    """CNAME verso servizio noto ma che risolve ancora → nessun takeover."""
    from apps.osint.models import OsintScan, OsintSubdomain, SubdomainStatus, OsintSettings
    from apps.osint.enrichers import takeover

    entity = _make_entity()
    OsintSubdomain.objects.create(entity=entity, subdomain="live.acme.example.com", status=SubdomainStatus.INCLUDED)
    scan = OsintScan.objects.create(entity=entity)

    with patch("apps.osint.enrichers.takeover._cname_target", return_value="acme.github.io"), \
         patch("apps.osint.enrichers.takeover._target_resolves", return_value=True):
        takeover.run(entity, scan, OsintSettings.load())

    assert scan.takeover_candidates == []


@pytest.mark.django_db
def test_takeover_only_included_subdomains():
    """I sottodomini pending/ignored non vengono valutati."""
    from apps.osint.models import OsintScan, OsintSubdomain, SubdomainStatus, OsintSettings
    from apps.osint.enrichers import takeover

    entity = _make_entity()
    OsintSubdomain.objects.create(entity=entity, subdomain="pending.acme.example.com", status=SubdomainStatus.PENDING)
    scan = OsintScan.objects.create(entity=entity)

    with patch("apps.osint.enrichers.takeover._cname_target") as mock_cname:
        takeover.run(entity, scan, OsintSettings.load())

    mock_cname.assert_not_called()
    assert scan.takeover_candidates == []


# ── finding engine: candidato → finding CRITICAL ────────────────────────────

@pytest.mark.django_db
def test_takeover_candidate_creates_critical_finding():
    from apps.osint.models import (
        OsintScan, FindingCode, FindingStatus, OsintFinding, AlertSeverity,
    )
    from apps.osint.findings import sync_findings, _detect_finding_codes

    entity = _make_entity()
    scan = OsintScan.objects.create(
        entity=entity,
        takeover_candidates=[{"subdomain": "shop.acme.example.com", "cname": "x.s3.amazonaws.com", "service": "AWS S3"}],
    )

    detected = _detect_finding_codes(entity, scan)
    assert FindingCode.SUBDOMAIN_TAKEOVER in detected

    created, _, _ = sync_findings(entity, scan)
    assert created >= 1
    finding = OsintFinding.objects.get(entity=entity, code=FindingCode.SUBDOMAIN_TAKEOVER)
    assert finding.severity == AlertSeverity.CRITICAL
    assert finding.status == FindingStatus.OPEN
    assert finding.params["candidates"]


@pytest.mark.django_db
def test_takeover_finding_auto_resolves_when_gone():
    """Quando lo scan successivo non rileva più il candidato, il finding si auto-chiude."""
    from apps.osint.models import OsintScan, FindingCode, FindingStatus, OsintFinding
    from apps.osint.findings import sync_findings

    entity = _make_entity()
    scan1 = OsintScan.objects.create(
        entity=entity,
        takeover_candidates=[{"subdomain": "shop.acme.example.com", "cname": "x.s3.amazonaws.com", "service": "AWS S3"}],
    )
    sync_findings(entity, scan1)

    scan2 = OsintScan.objects.create(entity=entity, takeover_candidates=[])
    sync_findings(entity, scan2)

    finding = OsintFinding.objects.get(entity=entity, code=FindingCode.SUBDOMAIN_TAKEOVER)
    assert finding.status == FindingStatus.RESOLVED


# ── alert engine: candidato → alert CRITICAL ────────────────────────────────

@pytest.mark.django_db
def test_takeover_trigger_creates_critical_alert():
    from apps.osint.models import OsintScan, OsintSettings, AlertType, AlertSeverity
    from apps.osint.alerts import _trigger_takeover

    entity = _make_entity()
    scan = OsintScan.objects.create(
        entity=entity,
        takeover_candidates=[{"subdomain": "shop.acme.example.com", "cname": "x.s3.amazonaws.com", "service": "AWS S3"}],
    )
    created: list = []
    _trigger_takeover(entity, scan, OsintSettings.load(), created)

    assert len(created) == 1
    assert created[0].alert_type == AlertType.SUBDOMAIN_TAKEOVER
    assert created[0].severity == AlertSeverity.CRITICAL

    # Idempotenza: un secondo trigger con alert attivo non duplica.
    created2: list = []
    _trigger_takeover(entity, scan, OsintSettings.load(), created2)
    assert created2 == []


# ── catalogo remediation: la voce esiste ed è completa ──────────────────────

def test_takeover_playbook_in_catalog():
    from apps.osint.findings import get_playbook
    pb = get_playbook("subdomain_takeover")
    assert pb is not None
    assert pb["title"]
    assert pb["fix_steps"]
    assert pb["owner_role"]

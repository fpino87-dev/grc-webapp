"""Test per le correzioni emerse dalla review del modulo OSINT.

Coprono: scoring GRC (status corretti), enricher DNSBL, blocco SSRF su
redirect negli HTTP headers, DNSSEC 'unknown', fan-out weekly scan.
"""
from unittest.mock import patch

import pytest


# ── #2 scoring GRC: ora conta i controlli in stato 'gap' ─────────────────────

@pytest.mark.django_db
def test_score_grc_counts_gap_controls():
    import datetime
    from apps.plants.models import Plant
    from apps.controls.models import ControlInstance, Control, Framework
    from apps.osint.models import OsintEntity, OsintScan, EntityType, SourceModule
    from apps.osint.scoring import _score_grc

    plant = Plant.objects.create(code="GRC-P", name="P", country="IT", nis2_scope="non_soggetto", status="attivo")
    fw = Framework.objects.create(code="ISO27001", name="ISO", version="1", published_at=datetime.date(2024, 1, 1))
    ctrl = Control.objects.create(framework=fw, external_id="A.5.1", translations={"title": {"it": "x"}})
    # Controllo in 'gap' → con il vecchio status errato ('non_conforme') sarebbe
    # stato ignorato (0). Ora deve contare (gap_controls >= 1 → +20).
    ControlInstance.objects.create(plant=plant, control=ctrl, status="gap")

    entity = OsintEntity.objects.create(
        entity_type=EntityType.MY_DOMAIN, source_module=SourceModule.SITES,
        source_id=plant.id, domain="p.example.com", display_name="P",
    )
    scan = OsintScan.objects.create(entity=entity)
    score = _score_grc(entity, scan)
    # gap_controls >= 1 → +20 (il bug precedente avrebbe dato 0 per i 'gap').
    assert score >= 20


@pytest.mark.django_db
def test_score_grc_counts_open_risks():
    from apps.plants.models import Plant
    from apps.risk.models import RiskAssessment
    from apps.osint.models import OsintEntity, OsintScan, EntityType, SourceModule
    from apps.osint.scoring import _score_grc

    plant = Plant.objects.create(code="GRC-R", name="R", country="IT", nis2_scope="non_soggetto", status="attivo")
    RiskAssessment.objects.create(plant=plant, name="r1", status="completato", risk_accepted=False, probability=4, impact=4)

    entity = OsintEntity.objects.create(
        entity_type=EntityType.MY_DOMAIN, source_module=SourceModule.SITES,
        source_id=plant.id, domain="r.example.com", display_name="R",
    )
    scan = OsintScan.objects.create(entity=entity)
    # is_nis2_critical False, 1 rischio aperto non accettato → +20.
    assert _score_grc(entity, scan) >= 20


# ── #1 DNSBL parser ──────────────────────────────────────────────────────────

def test_dnsbl_listed_response_parsing():
    from apps.osint.enrichers.dnsbl import _is_listed_response
    assert _is_listed_response(["127.0.0.2"]) is True       # listing reale
    assert _is_listed_response(["127.0.0.10"]) is True
    assert _is_listed_response(["127.255.255.254"]) is False  # codice di errore/limite
    assert _is_listed_response([]) is False
    assert _is_listed_response(["8.8.8.8"]) is False


@pytest.mark.django_db
def test_dnsbl_sets_blacklist_flag():
    from apps.osint.models import OsintEntity, OsintScan, EntityType, SourceModule, OsintSettings
    from apps.osint.enrichers import dnsbl

    entity = OsintEntity.objects.create(
        entity_type=EntityType.SUPPLIER, source_module=SourceModule.SUPPLIERS,
        source_id="00000000-0000-0000-0000-000000000001", domain="bad.example.com", display_name="Bad",
    )
    scan = OsintScan.objects.create(entity=entity)
    with patch("apps.osint.validators.is_public_internet_target", return_value=True), \
         patch("apps.osint.validators.safe_resolve_public_ip", return_value="93.184.216.34"), \
         patch("apps.osint.enrichers.dnsbl._query", return_value=["127.0.0.2"]):
        ok = dnsbl.run(entity, scan, OsintSettings.load())
    assert ok is True
    assert scan.in_blacklist is True
    assert scan.blacklist_sources  # almeno una sorgente


# ── #3 SSRF: i redirect verso host non pubblici sono bloccati ────────────────

def test_http_headers_blocks_redirect_to_internal():
    from apps.osint.enrichers import http_headers

    class FakeResp:
        def __init__(self, status, headers):
            self.status_code = status
            self.headers = headers
        def close(self):
            pass

    # 302 verso il metadata endpoint cloud → deve essere bloccato (None).
    redirect = FakeResp(302, {"Location": "http://169.254.169.254/latest/meta-data/"})
    with patch("apps.osint.enrichers.http_headers._request_no_redirect", return_value=redirect):
        result = http_headers._follow_validated("GET", "https://victim.example.com/")
    assert result is None


def test_http_headers_follows_public_redirect():
    from apps.osint.enrichers import http_headers

    class FakeResp:
        def __init__(self, status, headers):
            self.status_code = status
            self.headers = headers
        def close(self):
            pass

    seq = [
        FakeResp(301, {"Location": "https://www.example.com/"}),
        FakeResp(200, {"Strict-Transport-Security": "max-age=63072000"}),
    ]
    with patch("apps.osint.enrichers.http_headers._request_no_redirect", side_effect=seq), \
         patch("apps.osint.validators.is_public_internet_target", return_value=True):
        result = http_headers._follow_validated("GET", "https://example.com/")
    assert result is not None
    assert "strict-transport-security" in result


# ── #11 DNSSEC unknown non genera finding ────────────────────────────────────

@pytest.mark.django_db
def test_dnssec_unknown_does_not_trigger_finding():
    from apps.osint.models import OsintEntity, OsintScan, EntityType, SourceModule, FindingCode
    from apps.osint.findings import _detect_finding_codes

    entity = OsintEntity.objects.create(
        entity_type=EntityType.MY_DOMAIN, source_module=SourceModule.SITES,
        source_id="00000000-0000-0000-0000-000000000002", domain="d.example.com", display_name="D",
    )
    # dnssec_enabled None (incerto) + presenza dominio → niente finding DNSSEC.
    scan = OsintScan.objects.create(entity=entity, dnssec_enabled=None, ssl_valid=True, mx_present=True)
    detected = _detect_finding_codes(entity, scan)
    assert FindingCode.DNSSEC_MISSING not in detected
    # Mentre False esplicito → finding presente.
    scan2 = OsintScan.objects.create(entity=entity, dnssec_enabled=False, ssl_valid=True, mx_present=True)
    assert FindingCode.DNSSEC_MISSING in _detect_finding_codes(entity, scan2)


# ── #6 weekly scan ora fa fan-out ────────────────────────────────────────────

@pytest.mark.django_db
def test_weekly_scan_dispatches_per_entity():
    from apps.osint.models import OsintEntity, EntityType, SourceModule
    from apps.osint import tasks

    OsintEntity.objects.create(
        entity_type=EntityType.SUPPLIER, source_module=SourceModule.SUPPLIERS,
        source_id="00000000-0000-0000-0000-000000000003", domain="e1.example.com",
        display_name="E1", scan_frequency="weekly", is_active=True,
    )
    with patch("apps.osint.services.aggregate_entities"), \
         patch("apps.osint.tasks.run_entity_scan.delay") as mock_delay:
        result = tasks.run_weekly_scan()
    assert mock_delay.called
    assert result["dispatched"] >= 1

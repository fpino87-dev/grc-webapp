"""Dati OSINT fermi a mesi prima: cause e visibilità.

Lo scan falliva per intero — ogni settimana, in silenzio — sui domini senza
record A (sola posta) e su quelli che il server risolve su IP interni, perché
la guardia anti-SSRF pensata per chi si collega al target bloccava anche gli
enricher che interrogano terzi sul suo nome (DNS, WHOIS, reputazione). In
interfaccia restava l'ultimo scan riuscito, senza alcun segnale.
"""
import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.osint import validators
from apps.osint.models import EntityType, OsintEntity, OsintScan, ScanStatus, SourceModule

User = get_user_model()


# ── Guardie: nome pubblico ≠ target raggiungibile ───────────────────────────

@pytest.mark.parametrize("ips,expected", [
    (["93.184.216.34"], "public"),
    ([], "no_address"),
    (["10.0.0.5"], "private"),
    (["93.184.216.34", "192.168.1.10"], "private"),
])
def test_target_reachability(ips, expected):
    with patch.object(validators, "_resolve_all", return_value=ips):
        assert validators.target_reachability("fornitore.it") == expected


def test_internal_names_are_never_reachable_nor_passively_scanned():
    with patch.object(validators, "_resolve_all") as resolve:
        assert validators.target_reachability("as400.azienda.local") == "private"
        assert validators.assert_public_name_or_log("as400.azienda.local", "dns") is False
        resolve.assert_not_called()


def test_passive_guard_does_not_need_an_address():
    """Un dominio di sola posta è un nome pubblico: DNS/WHOIS/reputazione si leggono."""
    with patch.object(validators, "_resolve_all", return_value=[]):
        assert validators.assert_public_name_or_log("solo-posta.it", "dns") is True


# ── Enricher ────────────────────────────────────────────────────────────────

def _scan_stub(**extra):
    return SimpleNamespace(enricher_errors={}, **extra)


def test_dns_enricher_reads_mail_only_domain():
    from apps.osint.enrichers import dns as dns_enr

    scan = _scan_stub()
    with patch.object(validators, "_resolve_all", return_value=[]), \
         patch.object(dns_enr, "_txt_records", return_value=["v=spf1 -all"]), \
         patch.object(dns_enr, "_check_dmarc", return_value=(False, "")), \
         patch.object(dns_enr, "_check_mx", return_value=False), \
         patch.object(dns_enr, "_check_dnssec", return_value=False):
        assert dns_enr.run(SimpleNamespace(domain="solo-posta.it"), scan, None) is True
    assert scan.dmarc_present is False
    assert "dns" not in scan.enricher_errors


def test_ssl_enricher_on_privately_resolved_domain_skips_probe_but_reads_ct(monkeypatch):
    """DNS split-horizon: nessuna connessione al target e nessun falso «senza
    HTTPS»; i log dei certificati si leggono comunque."""
    from apps.osint.enrichers import ssl as ssl_enr

    crtsh_calls = []
    monkeypatch.setattr(validators, "_resolve_all", lambda d: ["10.1.2.3"])
    monkeypatch.setattr(ssl_enr, "_tls_probe", lambda d: pytest.fail("connessione a target privato"))
    monkeypatch.setattr(ssl_enr, "_serves_over_http", lambda d: pytest.fail("connessione a target privato"))
    monkeypatch.setattr(ssl_enr, "_fetch_crtsh_entries", lambda d: crtsh_calls.append(d) or [])
    scan = _scan_stub(ssl_valid=None, https_available=None, http_only=None)

    assert ssl_enr.run(SimpleNamespace(domain="azienda.com"), scan, None) is True
    assert scan.enricher_errors["ssl"] == "non_public_target"
    assert scan.https_available is None and scan.ssl_valid is None
    assert crtsh_calls == ["azienda.com"]


def test_http_headers_enricher_without_address_is_not_an_error(monkeypatch):
    from apps.osint.enrichers import http_headers

    monkeypatch.setattr(validators, "_resolve_all", lambda d: [])
    monkeypatch.setattr(http_headers, "_follow_validated", lambda m, u: pytest.fail("nessun host da interrogare"))
    scan = _scan_stub()
    assert http_headers.run(SimpleNamespace(domain="solo-posta.it"), scan, None) is True
    assert scan.security_headers == {} and scan.enricher_errors == {}


def test_http_headers_enricher_refuses_private_target(monkeypatch):
    from apps.osint.enrichers import http_headers

    monkeypatch.setattr(validators, "_resolve_all", lambda d: ["192.168.0.10"])
    monkeypatch.setattr(http_headers, "_follow_validated", lambda m, u: pytest.fail("SSRF"))
    scan = _scan_stub()
    assert http_headers.run(SimpleNamespace(domain="azienda.com"), scan, None) is False
    assert scan.enricher_errors["http_headers"] == "non_public_target"


# ── Scan interrotto e visibilità dell'ultimo tentativo ──────────────────────

def _entity(domain="fermo.example.com"):
    return OsintEntity.objects.create(
        entity_type=EntityType.SUPPLIER, source_module=SourceModule.SUPPLIERS,
        source_id=uuid.uuid4(), domain=domain, display_name=domain,
    )


@pytest.mark.django_db
def test_crashed_scan_is_recorded_as_failed():
    from apps.osint.enrichers import run as run_mod
    from apps.osint.models import OsintSettings

    entity = _entity()
    with patch.object(run_mod, "_run_enrichers", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            run_mod.run_enrichment(entity, OsintSettings.load())

    scan = OsintScan.objects.get(entity=entity)
    assert scan.status == ScanStatus.FAILED
    assert "boom" in scan.enricher_errors["scan"]


@pytest.mark.django_db
def test_api_exposes_failed_attempt_after_last_successful_scan():
    user = User.objects.create_superuser(username="stale", password="x", email="stale@test.com")
    client = APIClient()
    client.force_authenticate(user=user)
    entity = _entity()
    ok = OsintScan.objects.create(entity=entity, status=ScanStatus.COMPLETED, score_total=20)
    failed = OsintScan.objects.create(
        entity=entity, status=ScanStatus.FAILED, enricher_errors={"dns": "non_public_target"},
    )

    rows = client.get("/api/v1/osint/entities/").data
    rows = rows["results"] if isinstance(rows, dict) else rows
    row = next(r for r in rows if r["id"] == str(entity.pk))
    assert row["last_scan"]["id"] == str(ok.pk)
    assert row["last_attempt"]["status"] == "failed"
    assert row["last_attempt"]["scan_date"] == failed.scan_date

    detail = client.get(f"/api/v1/osint/entities/{entity.pk}/").data
    assert detail["last_scan"]["id"] == str(ok.pk)
    assert detail["last_attempt"]["errors"] == {"dns": "non_public_target"}

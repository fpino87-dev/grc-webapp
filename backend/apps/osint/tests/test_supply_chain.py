"""Monitoraggio supply chain: fornitori critici, profilo senza rumore,
impersonificazione, compromissione, accessi remoti esposti, servizi usati."""
import datetime
import uuid
from unittest import mock

import pytest
from django.utils import timezone

from apps.osint.models import EntityType, OsintEntity, OsintScan, OsintSettings, ScanStatus, SourceModule

pytestmark = pytest.mark.django_db


def _supplier(deep=False, domain="fornitore.example.com", name="Fornitore Rossi S.p.A.", hosts=None):
    return OsintEntity.objects.create(entity_type=EntityType.SUPPLIER, source_module=SourceModule.SUPPLIERS,
                                      source_id=uuid.uuid4(), domain=domain, display_name=name,
                                      deep_monitoring=deep, service_hosts=hosts or [])


def _scan(entity, **kw):
    base = dict(status=ScanStatus.COMPLETED, ssl_valid=False, dmarc_present=True, dmarc_policy="reject",
                spf_present=True, spf_policy="-all", mx_present=True, dnssec_enabled=False,
                security_headers={"missing": ["hsts"]})
    base.update(kw)
    return OsintScan.objects.create(entity=entity, **base)


def _codes(entity, scan):
    from apps.osint.findings import _detect_finding_codes
    return set(_detect_finding_codes(entity, scan))


# ── Chi è critico ────────────────────────────────────────────────────────────

def test_supplier_is_critical_rules():
    from apps.osint.services import supplier_is_critical
    S = type("S", (), {})
    def sup(**kw):
        s = S(); s.pk = uuid.uuid4()
        for k, v in {"nis2_relevant": False, "tisax_relevant": False, "risk_level": "basso",
                     "risk_adj": "", "internal_risk_level": "", **kw}.items():
            setattr(s, k, v)
        return s
    assert supplier_is_critical(sup(nis2_relevant=True), set())
    assert supplier_is_critical(sup(tisax_relevant=True), set())
    assert supplier_is_critical(sup(risk_adj="critico"), set())
    s = sup()
    assert supplier_is_critical(s, {s.pk}) and not supplier_is_critical(sup(), set())


def test_sync_sets_deep_monitoring_and_service_hosts():
    from apps.osint.services import aggregate_entities
    from apps.suppliers.models import Supplier
    sup = Supplier.objects.create(name="Tele Srl", website="https://tele.example.com", tisax_relevant=True,
                                  service_urls=["https://portale.tele.example.com/login", "sftp.tele.example.com"])
    aggregate_entities()
    e = OsintEntity.objects.get(source_id=sup.pk)
    assert e.deep_monitoring is True
    assert e.service_hosts == ["portale.tele.example.com", "sftp.tele.example.com"]


# ── Profilo fornitore: niente rumore ─────────────────────────────────────────

def test_supplier_hygiene_is_not_a_problem():
    e = _supplier()
    codes = _codes(e, _scan(e))
    assert not codes & {"ssl_expired", "headers_missing", "dnssec_missing", "dmarc_missing", "new_subdomain"}


def test_domain_spoofable_severity_depends_on_depth():
    from apps.osint.findings import _detect_finding_codes, _severity_for
    for deep, sev in ((True, "critical"), (False, "warning")):
        e = _supplier(deep=deep, domain=f"sp{int(deep)}.example.com")
        det = _detect_finding_codes(e, _scan(e, dmarc_present=False))
        assert _severity_for("domain_spoofable", det["domain_spoofable"]) == sev


# ── Compromissione ───────────────────────────────────────────────────────────

def test_normalize_name_strips_legal_form():
    from apps.osint.enrichers.supplychain import normalize_name
    assert normalize_name("Rossi S.p.A.") == "rossi"
    assert normalize_name("Müller GmbH") == "muller"


def test_ransomware_match_by_domain_and_by_name():
    from apps.osint.enrichers.supplychain import ransomware_hits
    from apps.osint.models import OsintRansomwareVictim
    now = timezone.now()
    OsintRansomwareVictim.objects.create(victim="fornitore.example.com", domain="fornitore.example.com",
                                         group="akira", discovered=now, name_key="fornitore example com")
    OsintRansomwareVictim.objects.create(victim="Rossi SpA", group="lockbit", discovered=now, name_key="rossi")
    OsintRansomwareVictim.objects.create(victim="Vecchio", domain="fornitore.example.com", group="old",
                                         discovered=now - datetime.timedelta(days=400), name_key="vecchio")
    hits = ransomware_hits(_supplier(name="Rossi S.p.A."))
    assert {h["group"] for h in hits} == {"akira", "lockbit"}


def test_refresh_ransomware_victims_from_feed():
    from apps.osint.enrichers import supplychain
    from apps.osint.models import OsintRansomwareVictim
    feed = [{"victim": "acme.example.com", "group": "akira", "discovered": "2026-09-20T10:00:00+00:00",
             "domain": "", "country": "IT", "activity": "Manufacturing"}]
    resp = mock.Mock(status_code=200, json=lambda: feed, raise_for_status=lambda: None)
    with mock.patch.object(supplychain.requests, "get", return_value=resp):
        assert supplychain.refresh_ransomware_victims() == 1
        assert supplychain.refresh_ransomware_victims() == 0  # idempotente
    assert OsintRansomwareVictim.objects.get().domain == "acme.example.com"


def test_service_breach_recent_is_critical():
    from apps.osint.findings import _detect_finding_codes, _severity_for
    e = _supplier()
    recent = (timezone.localdate() - datetime.timedelta(days=60)).isoformat()
    det = _detect_finding_codes(e, _scan(e, hibp_domain_breaches=[{"name": "X", "date": recent}]))
    assert _severity_for("service_breach", det["service_breach"]) == "critical"
    old = (timezone.localdate() - datetime.timedelta(days=600)).isoformat()
    det = _detect_finding_codes(e, _scan(e, hibp_domain_breaches=[{"name": "X", "date": old}]))
    assert _severity_for("service_breach", det["service_breach"]) == "warning"


# ── Accessi remoti e servizi usati ───────────────────────────────────────────

def test_remote_access_uses_ct_hosts_internetdb_and_kev():
    from apps.osint.enrichers import supplychain
    from apps.osint.models import OsintSubdomain
    e = _supplier(deep=True)
    for sub in ("vpn.fornitore.example.com", "www.fornitore.example.com", "rdp01.fornitore.example.com"):
        OsintSubdomain.objects.create(entity=e, subdomain=sub)
    idb = {"203.0.113.10": {"ports": [443], "vulns": ["CVE-2024-21762", "CVE-2000-0001"]},
           "203.0.113.11": {"ports": [3389], "vulns": []}}
    ips = {"vpn.fornitore.example.com": "203.0.113.10", "rdp01.fornitore.example.com": "203.0.113.11"}
    with mock.patch.object(supplychain, "kev_catalog", return_value={"CVE-2024-21762"}), \
         mock.patch.object(supplychain, "internetdb", side_effect=lambda ip: idb[ip]), \
         mock.patch("apps.osint.validators.safe_resolve_public_ip", side_effect=lambda h: ips.get(h)):
        rows = supplychain.remote_access(e)
    assert {r["host"] for r in rows} == {"vpn.fornitore.example.com", "rdp01.fornitore.example.com"}
    scan = _scan(e, remote_access=rows)
    codes = _codes(e, scan)
    assert {"remote_access_kev", "admin_service_exposed"} <= codes


def test_service_certificate_counts_only_on_used_services():
    from apps.osint.findings import _detect_finding_codes, _severity_for
    e = _supplier(hosts=["portale.fornitore.example.com"])
    det = _detect_finding_codes(e, _scan(e, service_checks=[
        {"host": "portale.fornitore.example.com", "reachable": True, "days_remaining": -2, "expiry": "2026-09-20"}]))
    assert _severity_for("service_cert", det["service_cert"]) == "critical"


# ── Voto per pilastri ────────────────────────────────────────────────────────

def test_supplier_score_compromise_dominates_and_spoofable_counts():
    from apps.osint.scoring import compute_scores, grade_for
    s = OsintSettings.load()
    e = _supplier(deep=True)
    scan = _scan(e, dmarc_present=False)
    compute_scores(e, scan, s)
    assert scan.score_impersonation == 60 and scan.score_compromise == 0
    assert grade_for(scan.score_total, s) in ("C", "D")
    scan = _scan(e, ransomware_hits=[{"victim": "x", "group": "akira"}])
    compute_scores(e, scan, s)
    assert scan.score_total == 100 and grade_for(scan.score_total, s) == "F"


# ── Domini sosia ─────────────────────────────────────────────────────────────

def test_lookalike_candidates_and_same_owner_filter():
    from apps.osint.enrichers import lookalike_lite
    c = lookalike_lite.candidates("fornitore.it")
    assert {"fornitre.it", "fornitore.com", "f0rnitore.it", "fornitore-it.com"} <= set(c)
    e = _supplier(domain="fornitore.it")
    scan = _scan(e)
    table = {"fornitore.it": (["1.1.1.1"], ["mx.fornitore.it"]),
             "fornitore.com": (["1.1.1.1"], []),            # stesso titolare (stesso IP)
             "fornitre.it": (["9.9.9.9"], ["mx.evil.test"])}  # sosia con posta
    recent = timezone.localdate() - datetime.timedelta(days=20)
    with mock.patch.object(lookalike_lite, "_lookup", side_effect=lambda d: table.get(d, ([], []))), \
         mock.patch.object(lookalike_lite, "registration_date", return_value=recent):
        lookalike_lite.run(e, scan, None)
    assert [x["domain"] for x in scan.lookalike_domains] == ["fornitre.it"] and scan.lookalike_domains[0]["mx"]
    assert scan.lookalike_domains[0]["recent"] is True


def test_supplier_lookalike_counts_only_recent_registrations():
    e = _supplier(deep=True)
    old = _scan(e, lookalike_domains=[{"domain": "omonimo.com", "mx": True, "recent": False}])
    assert "lookalike_domains" not in _codes(e, old)
    new = _scan(e, lookalike_domains=[{"domain": "f0rnitore.it", "mx": True, "recent": True}])
    assert "lookalike_domains" in _codes(e, new)

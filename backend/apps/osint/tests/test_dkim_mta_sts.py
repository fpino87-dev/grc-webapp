"""Test P2-3 — detection DNS-only DKIM / MTA-STS / TLS-RPT + scoring + findings."""
import pytest
from unittest.mock import MagicMock, patch

import dns.resolver

from apps.osint.enrichers.dns import _check_dkim, _check_mta_sts, _check_tls_rpt
from apps.osint.scoring import _score_dns
from apps.osint.findings import _detect_finding_codes, _severity_for
from apps.osint.models import (
    AlertSeverity, EntityType, FindingCode, OsintEntity, OsintScan,
    ScanStatus, SourceModule,
)
from apps.plants.models import Plant


pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Enricher DNS (mock di dns.resolver.resolve)
# ---------------------------------------------------------------------------

def _txt_answer(value: str):
    """Costruisce una risposta TXT fake compatibile con il parsing dell'enricher."""
    rec = MagicMock()
    rec.strings = [value.encode()]
    return [rec]


class TestCheckDkim:
    def test_found_on_first_selector(self):
        def fake_resolve(name, rtype, **kw):
            if name.startswith("default._domainkey."):
                return _txt_answer("v=DKIM1; k=rsa; p=ABC123")
            raise dns.resolver.NXDOMAIN()
        with patch("dns.resolver.resolve", side_effect=fake_resolve):
            present, selectors = _check_dkim("example.com")
        assert present is True
        assert "default" in selectors

    def test_not_found_resolver_responds(self):
        # Tutte le query rispondono NXDOMAIN → assenza certa → False, []
        with patch("dns.resolver.resolve", side_effect=dns.resolver.NXDOMAIN()):
            present, selectors = _check_dkim("example.com")
        assert present is False
        assert selectors == []

    def test_resolver_down_is_uncertain(self):
        # Ogni query solleva un errore generico → esito incerto → None
        with patch("dns.resolver.resolve", side_effect=Exception("dns down")):
            present, selectors = _check_dkim("example.com")
        assert present is None
        assert selectors == []


class TestCheckMtaSts:
    def test_present(self):
        with patch("dns.resolver.resolve", return_value=_txt_answer("v=STSv1; id=20260101")):
            assert _check_mta_sts("example.com") is True

    def test_absent_nxdomain(self):
        with patch("dns.resolver.resolve", side_effect=dns.resolver.NXDOMAIN()):
            assert _check_mta_sts("example.com") is False

    def test_uncertain_on_error(self):
        with patch("dns.resolver.resolve", side_effect=Exception("boom")):
            assert _check_mta_sts("example.com") is None


class TestCheckTlsRpt:
    def test_present(self):
        with patch("dns.resolver.resolve",
                   return_value=_txt_answer("v=TLSRPTv1; rua=mailto:x@example.com")):
            assert _check_tls_rpt("example.com") is True

    def test_absent(self):
        with patch("dns.resolver.resolve", side_effect=dns.resolver.NXDOMAIN()):
            assert _check_tls_rpt("example.com") is False


# ---------------------------------------------------------------------------
# Scoring: penalità DKIM/MTA-STS guardate da `is False`
# ---------------------------------------------------------------------------

def _mock_scan(**kwargs):
    s = MagicMock(spec=OsintScan)
    s.ssl_valid = True
    s.ssl_days_remaining = 120
    s.spf_present = True
    s.spf_policy = "fail"
    s.dmarc_present = True
    s.dmarc_policy = "reject"
    s.mx_present = True
    s.gsb_status = "safe"
    s.in_blacklist = False
    s.vt_malicious = 0
    s.abuseipdb_score = 0
    s.otx_pulses = 0
    # default: campi DKIM/MTA-STS non sondati
    s.dkim_present = kwargs.get("dkim_present", None)
    s.mta_sts_present = kwargs.get("mta_sts_present", None)
    for k, v in kwargs.items():
        setattr(s, k, v)
    return s


class TestScoreDnsEmailAuth:
    def test_none_fields_no_penalty(self):
        # Campi None (scan vecchio / non sondato) → nessuna penalità, nessuna regressione
        assert _score_dns(_mock_scan(dkim_present=None, mta_sts_present=None)) == 0

    def test_dkim_missing_adds_15(self):
        assert _score_dns(_mock_scan(dkim_present=False)) == 15

    def test_mta_sts_missing_adds_10(self):
        assert _score_dns(_mock_scan(mta_sts_present=False)) == 10

    def test_both_missing_cumulative(self):
        assert _score_dns(_mock_scan(dkim_present=False, mta_sts_present=False)) == 25

    def test_no_penalty_without_mx(self):
        # Senza mail server DKIM/MTA-STS non si applicano
        assert _score_dns(_mock_scan(mx_present=False, dkim_present=False, mta_sts_present=False)) == 0


# ---------------------------------------------------------------------------
# Findings: detection + severity
# ---------------------------------------------------------------------------

def _make_scan_obj(plant, **kwargs):
    entity = OsintEntity.objects.create(
        entity_type=EntityType.MY_DOMAIN, source_module=SourceModule.SITES,
        source_id=plant.id, domain="mail.example.com", display_name="Mail",
    )
    scan = OsintScan.objects.create(
        entity=entity, status=ScanStatus.COMPLETED,
        ssl_valid=True, ssl_days_remaining=120,
        spf_present=True, dmarc_present=True, dmarc_policy="reject",
        mx_present=True, **kwargs,
    )
    return entity, scan


def test_findings_detect_dkim_and_mta_sts_missing():
    p = Plant.objects.create(code="DK1", name="DkimPlant", country="IT",
                             nis2_scope="essenziale", status="attivo")
    entity, scan = _make_scan_obj(p, dkim_present=False, mta_sts_present=False, tls_rpt_present=False)
    detected = _detect_finding_codes(entity, scan)
    assert FindingCode.DKIM_MISSING in detected
    assert FindingCode.MTA_STS_MISSING in detected
    assert detected[FindingCode.MTA_STS_MISSING]["tls_rpt"] is False


def test_findings_skip_when_not_probed():
    p = Plant.objects.create(code="DK2", name="DkimPlant2", country="IT",
                             nis2_scope="essenziale", status="attivo")
    entity, scan = _make_scan_obj(p, dkim_present=None, mta_sts_present=None)
    detected = _detect_finding_codes(entity, scan)
    assert FindingCode.DKIM_MISSING not in detected
    assert FindingCode.MTA_STS_MISSING not in detected


def test_severity_mapping():
    assert _severity_for(FindingCode.DKIM_MISSING) == AlertSeverity.WARNING
    assert _severity_for(FindingCode.MTA_STS_MISSING) == AlertSeverity.INFO

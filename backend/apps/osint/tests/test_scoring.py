"""Test Step 4 — Score engine OSINT."""
import pytest
from unittest.mock import MagicMock, patch

from apps.osint.scoring import (
    _score_ssl,
    _score_dns,
    _score_reputation,
    compute_scores,
    classify_score,
    score_delta,
)
from apps.osint.models import EntityType, OsintScan, OsintEntity, SourceModule, ScanStatus


pytestmark = pytest.mark.django_db


def _scan(**kwargs):
    s = MagicMock(spec=OsintScan)
    s.ssl_valid = kwargs.get("ssl_valid", True)
    s.ssl_days_remaining = kwargs.get("ssl_days_remaining", 120)
    s.spf_present = kwargs.get("spf_present", True)
    s.spf_policy = kwargs.get("spf_policy", "fail")
    s.dmarc_present = kwargs.get("dmarc_present", True)
    s.dmarc_policy = kwargs.get("dmarc_policy", "reject")
    s.mx_present = kwargs.get("mx_present", True)
    s.gsb_status = kwargs.get("gsb_status", "safe")
    s.in_blacklist = kwargs.get("in_blacklist", False)
    s.vt_malicious = kwargs.get("vt_malicious", 0)
    s.abuseipdb_score = kwargs.get("abuseipdb_score", 0)
    s.otx_pulses = kwargs.get("otx_pulses", 0)
    return s


class TestScoreSSL:
    def test_invalid_ssl(self):
        s = _scan(ssl_valid=False, ssl_days_remaining=None)
        assert _score_ssl(s) == 100

    def test_expired(self):
        assert _score_ssl(_scan(ssl_days_remaining=0)) == 100

    def test_14_days(self):
        assert _score_ssl(_scan(ssl_days_remaining=14)) == 90

    def test_30_days(self):
        assert _score_ssl(_scan(ssl_days_remaining=30)) == 70

    def test_60_days(self):
        assert _score_ssl(_scan(ssl_days_remaining=60)) == 40

    def test_90_days(self):
        assert _score_ssl(_scan(ssl_days_remaining=90)) == 20

    def test_ok(self):
        assert _score_ssl(_scan(ssl_days_remaining=180)) == 0


class TestScoreDNS:
    def test_all_good(self):
        assert _score_dns(_scan()) == 0

    def test_no_spf(self):
        assert _score_dns(_scan(spf_present=False)) == 40

    def test_spf_plus_all(self):
        assert _score_dns(_scan(spf_policy="+all")) == 20

    def test_no_dmarc(self):
        assert _score_dns(_scan(dmarc_present=False)) == 30

    def test_dmarc_none_policy(self):
        assert _score_dns(_scan(dmarc_policy="none")) == 15

    def test_no_mx(self):
        # Senza mail server, SPF/DMARC non sono applicabili → score DNS = 0.
        # (Comportamento corretto introdotto dal fix "no falsi positivi su domini
        # senza servizi mail" — vedi commit 85d4915.)
        assert _score_dns(_scan(mx_present=False)) == 0

    def test_all_bad_capped_100_with_mx(self):
        s = _scan(spf_present=False, dmarc_present=False, mx_present=True)
        assert _score_dns(s) == min(40 + 30, 100)

    def test_spf_plus_all_with_mx(self):
        s = _scan(spf_present=True, spf_policy="+all", dmarc_present=False, mx_present=True)
        assert _score_dns(s) == 20 + 30


class TestScoreReputation:
    def test_all_clean(self):
        assert _score_reputation(_scan()) == 0

    def test_gsb_malware(self):
        assert _score_reputation(_scan(gsb_status="malware")) == 100

    def test_blacklist(self):
        assert _score_reputation(_scan(in_blacklist=True)) == 60

    def test_vt_high(self):
        assert _score_reputation(_scan(vt_malicious=6)) == 40

    def test_vt_low(self):
        assert _score_reputation(_scan(vt_malicious=1)) == 20

    def test_abuseipdb_high(self):
        assert _score_reputation(_scan(abuseipdb_score=51)) == 30

    def test_otx_pulses_low(self):
        assert _score_reputation(_scan(otx_pulses=1)) == 10

    def test_combination_capped(self):
        s = _scan(in_blacklist=True, vt_malicious=10, abuseipdb_score=80, otx_pulses=10)
        assert _score_reputation(s) == 100


class TestComputeScores:
    def _make_entity(self, entity_type=EntityType.MY_DOMAIN):
        from apps.plants.models import Plant
        p = Plant.objects.create(
            code="SCT1", name="Test", country="IT",
            nis2_scope="essenziale", status="attivo",
        )
        return OsintEntity.objects.create(
            entity_type=entity_type,
            source_module=SourceModule.SITES,
            source_id=p.id,
            domain="test.com",
            display_name="Test",
        )

    def test_supplier_weights(self):
        entity = self._make_entity(EntityType.SUPPLIER)
        scan = OsintScan()
        scan.ssl_valid = True
        scan.ssl_days_remaining = 200
        scan.spf_present = True
        scan.spf_policy = "fail"
        scan.dmarc_present = True
        scan.dmarc_policy = "reject"
        scan.mx_present = True
        scan.gsb_status = "safe"
        scan.in_blacklist = False
        scan.vt_malicious = 0
        scan.abuseipdb_score = 0
        scan.otx_pulses = 0
        compute_scores(entity, scan)
        assert scan.score_ssl == 0
        assert scan.score_dns == 0
        assert scan.score_reputation == 0
        assert scan.score_grc_context == 0
        assert scan.score_total == 0

    def test_my_domain_uses_grc_weight(self):
        entity = self._make_entity(EntityType.MY_DOMAIN)
        scan = OsintScan()
        scan.ssl_valid = False
        scan.ssl_days_remaining = None
        scan.spf_present = False
        scan.spf_policy = ""
        scan.dmarc_present = False
        scan.dmarc_policy = ""
        scan.mx_present = True  # con MX, SPF/DMARC vengono valutati
        scan.gsb_status = "safe"
        scan.in_blacklist = False
        scan.vt_malicious = 0
        scan.abuseipdb_score = 0
        scan.otx_pulses = 0
        compute_scores(entity, scan)
        # SSL=100, DNS=70 (spf_missing+dmarc_missing), Rep=0, GRC ≥ 0
        assert scan.score_ssl == 100
        assert scan.score_dns == min(40 + 30, 100)
        # total = 100*0.25 + 70*0.25 + 0*0.30 + grc*0.20 > 0
        assert scan.score_total > 0


class TestClassifyScore:
    def test_critical(self):
        assert classify_score(75) == "critical"
        assert classify_score(70) == "critical"

    def test_warning(self):
        assert classify_score(69) == "warning"
        assert classify_score(50) == "warning"

    def test_attention(self):
        assert classify_score(49) == "attention"
        assert classify_score(30) == "attention"

    def test_ok(self):
        assert classify_score(29) == "ok"
        assert classify_score(0) == "ok"

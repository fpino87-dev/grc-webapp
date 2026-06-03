"""Test P2-3 — enricher WHOIS/RDAP (RDAP-first, referral, redaction, sorgente)."""
import pytest
from datetime import date
from unittest.mock import patch

from apps.osint.enrichers import whois_enr
from apps.osint.enrichers.whois_enr import (
    _rdap_extract, _referral_url, _to_date, _parse_bootstrap,
)
from apps.osint.models import (
    EntityType, OsintEntity, OsintScan, ScanStatus, SourceModule,
)
from apps.plants.models import Plant


pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Parser puri
# ---------------------------------------------------------------------------

def test_to_date_variants():
    assert _to_date("2027-05-01T00:00:00Z") == date(2027, 5, 1)
    assert _to_date(["2027-05-01T00:00:00Z"]) == date(2027, 5, 1)
    assert _to_date("garbage") is None
    assert _to_date(None) is None


def test_parse_bootstrap():
    data = {"services": [[["com", "net"], ["https://rdap.verisign.com/com/v1/"]]]}
    mapping = _parse_bootstrap(data)
    assert mapping["com"] == "https://rdap.verisign.com/com/v1"
    assert mapping["net"] == "https://rdap.verisign.com/com/v1"


class TestRdapExtract:
    def test_expiry_registrar_country(self):
        data = {
            "events": [{"eventAction": "expiration", "eventDate": "2027-03-15T00:00:00Z"}],
            "entities": [{
                "roles": ["registrar"],
                "vcardArray": ["vcard", [
                    ["version", {}, "text", "4.0"],
                    ["fn", {}, "text", "Example Registrar Inc"],
                    ["adr", {}, "text", ["", "", "", "", "", "", "US"]],
                ]],
            }],
        }
        out = _rdap_extract(data)
        assert out["expiry"] == date(2027, 3, 15)
        assert out["registrar"] == "Example Registrar Inc"
        assert out["country"] == "US"
        assert out["privacy"] is False

    def test_privacy_via_rfc9537_redaction(self):
        data = {
            "redacted": [
                {"name": {"type": "Registrant Name"}, "method": "removal"},
            ],
        }
        assert _rdap_extract(data)["privacy"] is True

    def test_privacy_via_keyword(self):
        data = {"entities": [{
            "roles": ["registrar"],
            "vcardArray": ["vcard", [["fn", {}, "text", "Domains By Proxy, LLC"]]],
        }]}
        assert _rdap_extract(data)["privacy"] is True


class TestReferralUrl:
    def test_finds_related_rdap_link(self):
        data = {"links": [
            {"rel": "self", "href": "https://rdap.verisign.com/com/v1/domain/x.com"},
            {"rel": "related", "type": "application/rdap+json",
             "href": "https://rdap.registrar.example/domain/x.com"},
        ]}
        assert _referral_url(data) == "https://rdap.registrar.example/domain/x.com"

    def test_none_when_no_referral(self):
        assert _referral_url({"links": [{"rel": "self", "href": "https://x/"}]}) is None


# ---------------------------------------------------------------------------
# run() — sorgente e referral
# ---------------------------------------------------------------------------

def _entity():
    p = Plant.objects.create(code="WH1", name="WhoisPlant", country="IT",
                             nis2_scope="essenziale", status="attivo")
    return OsintEntity.objects.create(
        entity_type=EntityType.MY_DOMAIN, source_module=SourceModule.SITES,
        source_id=p.id, domain="example.com", display_name="Example",
    )


def _scan(entity):
    return OsintScan.objects.create(entity=entity, status=ScanStatus.RUNNING)


class TestRun:
    def test_rdap_source_set(self):
        entity = _entity()
        scan = _scan(entity)
        registry = {
            "events": [{"eventAction": "expiration", "eventDate": "2028-01-01T00:00:00Z"}],
            "entities": [{"roles": ["registrar"], "vcardArray": ["vcard", [["fn", {}, "text", "Reg X"]]]}],
        }
        with patch("apps.osint.validators.assert_public_or_log", return_value=True), \
             patch.object(whois_enr, "_query_rdap", return_value=registry), \
             patch.object(whois_enr, "_referral_url", return_value=None):
            assert whois_enr.run(entity, scan, None) is True
        assert scan.whois_source == "rdap"
        assert scan.domain_expiry_date == date(2028, 1, 1)
        assert scan.domain_registrar == "Reg X"

    def test_referral_fills_missing_and_marks_source(self):
        entity = _entity()
        scan = _scan(entity)
        registry = {"events": [], "entities": [], "links": [
            {"rel": "related", "type": "application/rdap+json",
             "href": "https://rdap.registrar.example/domain/example.com"},
        ]}
        registrar = {
            "events": [{"eventAction": "expiration", "eventDate": "2029-06-30T00:00:00Z"}],
            "entities": [{"roles": ["registrar"], "vcardArray": ["vcard", [["fn", {}, "text", "Registrar Y"]]]}],
        }
        with patch("apps.osint.validators.assert_public_or_log", return_value=True), \
             patch.object(whois_enr, "_query_rdap", return_value=registry), \
             patch.object(whois_enr, "_rdap_get", return_value=registrar):
            assert whois_enr.run(entity, scan, None) is True
        assert scan.whois_source == "rdap_referral"
        assert scan.domain_expiry_date == date(2029, 6, 30)
        assert scan.domain_registrar == "Registrar Y"

    def test_fallback_to_whois_source(self):
        entity = _entity()
        scan = _scan(entity)
        def _fill(domain, sc):
            sc.domain_registrar = "Legacy Reg"
            return True
        with patch("apps.osint.validators.assert_public_or_log", return_value=True), \
             patch.object(whois_enr, "_query_rdap", return_value=None), \
             patch.object(whois_enr, "_python_whois_fill", side_effect=_fill):
            assert whois_enr.run(entity, scan, None) is True
        assert scan.whois_source == "whois"

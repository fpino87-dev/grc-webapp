"""Letture DNS/TLS: DMARC per tag con eredità dal dominio padre; il
certificato di www.<dominio> non viene attribuito al dominio."""
import pytest

from apps.osint.enrichers import dns as dns_enr
from apps.osint.enrichers import ssl as ssl_enr

pytestmark = pytest.mark.django_db


def _records(mapping):
    return lambda name: mapping.get(name)


def test_dmarc_tags_not_substrings(monkeypatch):
    monkeypatch.setattr(dns_enr, "_dmarc_record", _records({
        "azienda.com": dns_enr._dmarc_tags("v=DMARC1; p=none; sp=reject"),
    }))
    assert dns_enr._check_dmarc("azienda.com") == (True, "none")


def test_dmarc_own_record_quarantine(monkeypatch):
    monkeypatch.setattr(dns_enr, "_dmarc_record", _records({
        "it.azienda.com": dns_enr._dmarc_tags("v=DMARC1; p=quarantine; rua=mailto:dmarc@it.azienda.com; fo=1"),
    }))
    assert dns_enr._check_dmarc("it.azienda.com") == (True, "quarantine")


def test_dmarc_inherited_from_parent_uses_sp(monkeypatch):
    monkeypatch.setattr(dns_enr, "_dmarc_record", _records({
        "azienda.com": dns_enr._dmarc_tags("v=DMARC1; p=reject; sp=quarantine"),
    }))
    assert dns_enr._check_dmarc("it.azienda.com") == (True, "quarantine")
    monkeypatch.setattr(dns_enr, "_dmarc_record", _records({
        "azienda.com": dns_enr._dmarc_tags("v=DMARC1; p=reject"),
    }))
    assert dns_enr._check_dmarc("mail.it.azienda.com") == (True, "reject")


def test_dmarc_missing_does_not_query_tld(monkeypatch):
    asked = []
    monkeypatch.setattr(dns_enr, "_dmarc_record", lambda name: asked.append(name))
    assert dns_enr._check_dmarc("it.azienda.com") == (False, "")
    assert asked == ["it.azienda.com", "azienda.com"]


def _run_ssl(monkeypatch, probe):
    from types import SimpleNamespace

    calls = []

    def fake_probe(host):
        calls.append(host)
        return probe(host)

    monkeypatch.setattr(ssl_enr, "_tls_probe", fake_probe)
    monkeypatch.setattr(ssl_enr, "_serves_over_http", lambda d: False)
    monkeypatch.setattr(ssl_enr, "_fetch_crtsh_entries", lambda d: [])
    monkeypatch.setattr("apps.osint.validators.assert_public_name_or_log", lambda d, n: True)
    monkeypatch.setattr("apps.osint.validators.target_reachability", lambda d: "public")
    scan = SimpleNamespace(ssl_valid=None, ssl_trusted=None, ssl_verify_error="", https_available=None,
                           http_only=None, enricher_errors={})
    assert ssl_enr.run(SimpleNamespace(domain="azienda.com"), scan, None) is True
    return scan, calls


def test_www_certificate_not_attributed_to_domain(monkeypatch):
    expired = {"notAfter": "Jan 01 00:00:00 2020 GMT"}
    scan, calls = _run_ssl(monkeypatch, lambda h: (None, None, "") if h == "azienda.com" else (expired, True, ""))
    assert calls == ["azienda.com"]
    assert scan.ssl_valid is None and scan.https_available is False and scan.http_only is False


def test_incomplete_chain_is_valid_but_untrusted_not_expired(monkeypatch):
    """Il certificato letto senza verifica (formato _der_to_ssl_dict) deve dare
    scadenza ed emittente: prima la lettura falliva e risultava «scaduto»."""
    cert = {
        "notAfter": "Nov 11 23:59:59 2099 GMT",
        "issuer": ((("countryName", "GB"),), (("organizationName", "Sectigo Limited"),)),
        "subjectAltName": [("DNS", "*.azienda.com")],
    }
    scan, _calls = _run_ssl(monkeypatch, lambda h: (cert, False, "unable to get local issuer certificate"))
    assert scan.ssl_valid is True and scan.ssl_issuer == "Sectigo Limited" and scan.ssl_wildcard is True
    assert scan.ssl_trusted is False and "local issuer" in scan.ssl_verify_error

    from apps.osint.findings import _detect_finding_codes
    from apps.osint.models import EntityType, FindingCode, OsintEntity, OsintScan, SourceModule
    import uuid

    entity = OsintEntity.objects.create(entity_type=EntityType.MY_DOMAIN, source_module=SourceModule.SITES,
                                        source_id=uuid.uuid4(), domain="azienda.com", display_name="Az")
    db_scan = OsintScan.objects.create(entity=entity, ssl_valid=True, ssl_days_remaining=400,
                                       ssl_trusted=False, ssl_verify_error="unable to get local issuer certificate")
    codes = _detect_finding_codes(entity, db_scan)
    assert FindingCode.SSL_UNTRUSTED in codes and FindingCode.SSL_EXPIRED not in codes


def test_der_issuer_matches_getpeercert_format():
    import datetime

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test CA")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(1).not_valid_before(now).not_valid_after(now + datetime.timedelta(days=30))
            .sign(key, hashes.SHA256()))
    parsed = ssl_enr._parse_cert(ssl_enr._der_to_ssl_dict(cert.public_bytes(serialization.Encoding.DER)))
    assert parsed[0] is True and parsed[3] == "Test CA"

"""Test Step 4 — Score engine OSINT."""
import pytest
from unittest.mock import MagicMock

from apps.osint.scoring import (
    _score_ssl,
    _score_dns,
    _score_reputation,
    compute_scores,
    classify_score,
)
from apps.osint.models import EntityType, OsintScan, OsintEntity, SourceModule


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
    s.threatfox_iocs = kwargs.get("threatfox_iocs", 0)
    s.urlhaus_urls = kwargs.get("urlhaus_urls", 0)
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

    def test_custom_thresholds_from_settings(self):
        from apps.osint.models import OsintSettings
        s = OsintSettings.load()
        s.score_threshold_critical = 90
        s.score_threshold_warning = 60
        s.score_threshold_attention = 20
        # 75 era 'critical' coi default, ora 'warning' con la soglia critica a 90
        assert classify_score(75, s) == "warning"
        assert classify_score(95, s) == "critical"
        assert classify_score(25, s) == "attention"
        assert classify_score(19, s) == "ok"


class TestConfigurableWeights:
    """compute_scores usa i pesi configurabili e normalizza sul totale dei pesi."""

    def _entity(self, entity_type=EntityType.MY_DOMAIN):
        from apps.plants.models import Plant
        p = Plant.objects.create(code="WSC1", name="W", country="IT",
                                 nis2_scope="essenziale", status="attivo")
        return OsintEntity.objects.create(
            entity_type=entity_type, source_module=SourceModule.SITES,
            source_id=p.id, domain="w.example.com", display_name="W",
        )

    def _scan_ssl100(self):
        scan = OsintScan()
        scan.ssl_valid = False  # SSL=100
        scan.ssl_days_remaining = None
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
        scan.dkim_present = None
        scan.mta_sts_present = None
        return scan

    def test_weight_shifts_total(self):
        from apps.osint.models import OsintSettings
        s = OsintSettings.load()
        # Tutto il peso su SSL → total == SSL == 100 (DNS/Rep/GRC=0)
        s.weight_ssl = 100
        s.weight_dns = 0
        s.weight_reputation = 0
        s.weight_grc = 0
        entity = self._entity()
        scan = self._scan_ssl100()
        compute_scores(entity, scan, s)
        assert scan.score_ssl == 100
        assert scan.score_total == 100

    def test_normalized_not_required_to_sum_100(self):
        from apps.osint.models import OsintSettings
        s = OsintSettings.load()
        # Pesi 10/10/10 → media semplice sulle tre dimensioni di esposizione.
        # SSL=100, DNS=0, Rep=0 → 33. (Il GRC non entra più nel totale: misura
        # la compliance del sito, non l'esposizione del dominio.)
        s.weight_ssl = s.weight_dns = s.weight_reputation = s.weight_grc = 10
        entity = self._entity()
        scan = self._scan_ssl100()
        compute_scores(entity, scan, s)
        assert scan.score_total == 33

    def test_supplier_excludes_grc_weight(self):
        from apps.osint.models import OsintSettings
        s = OsintSettings.load()
        # Per un fornitore il GRC è escluso: pesi usati = SSL/DNS/Rep = 1/1/1.
        s.weight_ssl = s.weight_dns = s.weight_reputation = 1
        s.weight_grc = 1000  # ignorato per i non-my_domain
        entity = self._entity(EntityType.SUPPLIER)
        scan = self._scan_ssl100()
        compute_scores(entity, scan, s)
        # SSL=100, DNS=0, Rep=0 → 100/3 ≈ 33
        assert scan.score_total == 33


@pytest.mark.django_db
class TestSettingsWeightValidation:
    def test_rejects_all_zero_core_weights(self):
        from apps.osint.serializers import OsintSettingsSerializer
        from apps.osint.models import OsintSettings
        s = OsintSettings.load()
        ser = OsintSettingsSerializer(
            instance=s,
            data={"weight_ssl": 0, "weight_dns": 0, "weight_reputation": 0},
            partial=True,
        )
        assert not ser.is_valid()

    def test_accepts_one_positive_core_weight(self):
        from apps.osint.serializers import OsintSettingsSerializer
        from apps.osint.models import OsintSettings
        s = OsintSettings.load()
        ser = OsintSettingsSerializer(
            instance=s,
            data={"weight_ssl": 50, "weight_dns": 0, "weight_reputation": 0},
            partial=True,
        )
        assert ser.is_valid(), ser.errors
        assert classify_score(0) == "ok"


class TestCompromiseFloor:
    """La media pesata diluisce: un segnale di compromissione in atto non va
    mediato con la scadenza di un certificato, deve dominare il giudizio.

    I casi qui sotto sono quelli che prima davano un esito palesemente sbagliato:
    un dominio che distribuisce malware finiva a 27/100, cioè «ok»."""

    def _entity(self):
        import uuid

        from apps.osint.models import EntityType, OsintEntity, SourceModule

        return OsintEntity.objects.create(
            entity_type=EntityType.MY_DOMAIN,
            source_module=SourceModule.SITES,
            source_id=uuid.uuid4(),
            domain="floor.example.com",
            display_name="Floor",
        )

    def _clean_scan(self, **kw):
        """Dominio impeccabile su tutto il resto: certificato valido a lungo,
        DNS in ordine, nessuna posta."""
        s = MagicMock(spec=OsintScan)
        s.ssl_valid = True
        s.ssl_days_remaining = 300
        s.https_available = True
        s.http_only = False
        s.mx_present = False
        s.spf_present = True
        s.spf_policy = "fail"
        s.dmarc_present = True
        s.dmarc_policy = "reject"
        s.dkim_present = None
        s.mta_sts_present = None
        s.gsb_status = kw.get("gsb_status", "safe")
        s.in_blacklist = kw.get("in_blacklist", False)
        s.vt_malicious = 0
        s.abuseipdb_score = 0
        s.otx_pulses = 0
        s.threatfox_iocs = kw.get("threatfox_iocs", 0)
        s.urlhaus_urls = kw.get("urlhaus_urls", 0)
        return s

    def _classify(self, settings, **kw):
        from apps.osint.scoring import classify_score, compute_scores

        scan = self._clean_scan(**kw)
        compute_scores(self._entity(), scan, settings)
        return scan.score_total, classify_score(scan.score_total, settings)

    def test_domain_serving_malware_is_critical(self):
        from apps.osint.models import OsintSettings

        s = OsintSettings.load()
        total, verdict = self._classify(s, threatfox_iocs=2, urlhaus_urls=3)
        assert verdict == "critical", f"score {total}"

    def test_active_malware_ioc_is_critical(self):
        from apps.osint.models import OsintSettings

        s = OsintSettings.load()
        _total, verdict = self._classify(s, threatfox_iocs=1)
        assert verdict == "critical"

    def test_google_safe_browsing_unsafe_is_critical(self):
        from apps.osint.models import OsintSettings

        s = OsintSettings.load()
        _total, verdict = self._classify(s, gsb_status="malware")
        assert verdict == "critical"

    def test_blacklisted_domain_is_critical(self):
        from apps.osint.models import OsintSettings

        s = OsintSettings.load()
        _total, verdict = self._classify(s, in_blacklist=True)
        assert verdict == "critical"

    def test_a_clean_domain_stays_ok(self):
        """Il pavimento non deve alzare il punteggio di chi è a posto."""
        from apps.osint.models import OsintSettings

        s = OsintSettings.load()
        total, verdict = self._classify(s)
        assert verdict == "ok"
        assert total == 0

"""
Rilevazione del mail server e sue conseguenze.

Il controllo MX distingue tre stati — accetta posta / non l'accetta / non
determinabile — perché «non lo so» e «no» portano a conclusioni opposte su SPF
e DMARC: senza posta la loro assenza è la configurazione corretta.
"""
from unittest.mock import MagicMock, patch

import pytest

from apps.osint.enrichers.dns import _check_mx


class _RR:
    """Record MX minimale (preference + exchange)."""

    def __init__(self, preference, exchange):
        self.preference = preference
        self.exchange = exchange


def _answer(records):
    ans = MagicMock()
    ans.rrset = records
    return ans


def _resolve_returning(records):
    return patch("dns.resolver.resolve", return_value=_answer(records))


def test_domain_with_mail_servers():
    with _resolve_returning([_RR(10, "smtp.example.com.")]):
        assert _check_mx("example.com") is True


def test_domain_without_any_mx_record():
    """La risoluzione con raise_on_no_answer=False NON solleva eccezione se non
    ci sono record: restituisce una risposta vuota. Trattarla come «ha la
    posta» faceva scattare un finding DMARC su ogni dominio solo-web."""
    with _resolve_returning(None):
        assert _check_mx("www.example.com") is False
    with _resolve_returning([]):
        assert _check_mx("www.example.com") is False


def test_null_mx_means_no_mail(): 
    """RFC 7505: un solo record con preferenza 0 e target «.» dichiara
    esplicitamente che il dominio non accetta posta."""
    with _resolve_returning([_RR(0, ".")]):
        assert _check_mx("example.com") is False


def test_preference_zero_towards_a_real_host_is_still_mail():
    """Preferenza 0 non basta: conta il target «.»."""
    with _resolve_returning([_RR(0, "mail.example.com.")]):
        assert _check_mx("example.com") is True


def test_nonexistent_domain_has_no_mail():
    import dns.resolver

    with patch("dns.resolver.resolve", side_effect=dns.resolver.NXDOMAIN()):
        assert _check_mx("inesistente.example") is False


def test_dns_failure_is_undetermined_not_negative():
    """Timeout o SERVFAIL: non si sa. Restituire False significherebbe
    dichiarare «non ha posta» per un errore di rete."""
    with patch("dns.resolver.resolve", side_effect=OSError("timeout")):
        assert _check_mx("example.com") is None


# ── Conseguenze a valle ──────────────────────────────────────────────────────

def _scan(mx_present, **kw):
    s = MagicMock()
    s.mx_present = mx_present
    s.spf_present = kw.get("spf_present", False)
    s.spf_policy = kw.get("spf_policy", "")
    s.dmarc_present = kw.get("dmarc_present", False)
    s.dmarc_policy = kw.get("dmarc_policy", "")
    s.dkim_present = kw.get("dkim_present", None)
    s.mta_sts_present = kw.get("mta_sts_present", None)
    return s


class TestScoreDns:
    def test_web_only_domain_is_not_penalised(self):
        """Un dominio senza posta e senza SPF/DMARC è configurato bene."""
        from apps.osint.scoring import _score_dns

        assert _score_dns(_scan(False)) == 0

    def test_undetermined_mail_is_not_penalised(self):
        from apps.osint.scoring import _score_dns

        assert _score_dns(_scan(None)) == 0

    def test_mail_domain_without_spf_and_dmarc_is_penalised(self):
        from apps.osint.scoring import _score_dns

        assert _score_dns(_scan(True)) == 70


class TestDmarcAlert:
    def _fire(self, mx_present):
        from apps.osint.alerts import _trigger_dmarc

        created = []
        entity = MagicMock()
        _trigger_dmarc(entity, _scan(mx_present), MagicMock(), created)
        return created

    def test_no_alert_on_a_domain_without_mail(self):
        assert self._fire(False) == []

    def test_no_alert_when_mail_cannot_be_determined(self):
        assert self._fire(None) == []


@pytest.mark.django_db
class TestFindings:
    """Il motore dei finding, chiamato per davvero su uno scan reale."""

    def _codes(self, mx_present):
        import uuid

        from apps.osint.findings import _detect_finding_codes
        from apps.osint.models import EntityType, OsintEntity, OsintScan, SourceModule

        entity = OsintEntity.objects.create(
            entity_type=EntityType.MY_DOMAIN,
            source_module=SourceModule.SITES,
            source_id=uuid.uuid4(),
            domain="posture.example.com",
            display_name="Posture test",
        )
        # Scan reale: i campi non impostati restano ai default del modello,
        # così il test non deve conoscere ogni attributo letto dal motore.
        scan = OsintScan.objects.create(
            entity=entity,
            status="completed",
            mx_present=mx_present,
            spf_present=False,
            dmarc_present=False,
        )
        return set(_detect_finding_codes(entity, scan))

    def test_web_only_domain_has_no_mail_findings(self):
        from apps.osint.models import FindingCode

        codes = self._codes(False)
        assert FindingCode.DMARC_MISSING not in codes
        assert FindingCode.SPF_MISSING not in codes

    def test_undetermined_mail_produces_no_mail_findings(self):
        from apps.osint.models import FindingCode

        assert FindingCode.DMARC_MISSING not in self._codes(None)

    def test_mail_domain_reports_missing_spf_and_dmarc(self):
        from apps.osint.models import FindingCode

        codes = self._codes(True)
        assert FindingCode.DMARC_MISSING in codes
        assert FindingCode.SPF_MISSING in codes


# ── Postura HTTPS ────────────────────────────────────────────────────────────

class TestScoreHttps:
    """Assenza di HTTPS: due casi opposti che prima collassavano in uno."""

    def _scan(self, **kw):
        s = MagicMock()
        s.ssl_valid = kw.get("ssl_valid", None)
        s.ssl_days_remaining = kw.get("ssl_days_remaining", None)
        s.http_only = kw.get("http_only", None)
        return s

    def test_site_served_in_clear_is_penalised(self):
        """Massimo della dimensione: un certificato scaduto cifra ancora,
        nessun HTTPS non cifra affatto."""
        from apps.osint.scoring import _score_ssl

        assert _score_ssl(self._scan(http_only=True)) == 100

    def test_domain_serving_nothing_is_not_penalised(self):
        from apps.osint.scoring import _score_ssl

        assert _score_ssl(self._scan(http_only=False)) == 0
        assert _score_ssl(self._scan(http_only=None)) == 0

    def test_clear_text_site_scores_worse_than_a_cert_expiring_soon(self):
        """L'inversione che c'era prima: un sito senza HTTPS otteneva 0 e uno
        con il certificato in scadenza 40."""
        from apps.osint.scoring import _score_ssl

        in_scadenza = self._scan(ssl_valid=True, ssl_days_remaining=45)
        assert _score_ssl(self._scan(http_only=True)) > _score_ssl(in_scadenza)


@pytest.mark.django_db
class TestNoHttpsFinding:
    def _codes(self, http_only):
        import uuid

        from apps.osint.findings import _detect_finding_codes
        from apps.osint.models import EntityType, OsintEntity, OsintScan, SourceModule

        entity = OsintEntity.objects.create(
            entity_type=EntityType.MY_DOMAIN,
            source_module=SourceModule.SITES,
            source_id=uuid.uuid4(),
            domain="chiaro.example.com",
            display_name="HTTP puro",
        )
        scan = OsintScan.objects.create(
            entity=entity, status="completed",
            https_available=False, http_only=http_only,
        )
        return set(_detect_finding_codes(entity, scan))

    def test_clear_text_site_is_reported(self):
        from apps.osint.models import FindingCode

        assert FindingCode.NO_HTTPS in self._codes(True)

    def test_unreachable_domain_is_not_reported(self):
        from apps.osint.models import FindingCode

        assert FindingCode.NO_HTTPS not in self._codes(False)
        assert FindingCode.NO_HTTPS not in self._codes(None)


class TestHttpProbe:
    """La sonda distingue «risponde in chiaro» da «redirige a HTTPS»."""

    def _resp(self, status, location=None):
        r = MagicMock()
        r.status_code = status
        r.headers = {"Location": location} if location else {}
        return r

    def test_plain_http_response_is_clear_text(self):
        from apps.osint.enrichers import ssl as ssl_enricher

        with patch("apps.osint.validators.is_public_internet_target", return_value=True), \
             patch("requests.get", return_value=self._resp(200)):
            assert ssl_enricher._serves_over_http("example.com") is True

    def test_redirect_to_https_is_not_clear_text(self):
        from apps.osint.enrichers import ssl as ssl_enricher

        with patch("apps.osint.validators.is_public_internet_target", return_value=True), \
             patch("requests.get", return_value=self._resp(301, "https://example.com/")):
            assert ssl_enricher._serves_over_http("example.com") is False

    def test_unreachable_host_is_undetermined(self):
        from apps.osint.enrichers import ssl as ssl_enricher

        with patch("apps.osint.validators.is_public_internet_target", return_value=True), \
             patch("requests.get", side_effect=OSError("connection refused")):
            assert ssl_enricher._serves_over_http("example.com") is None

    def test_non_public_target_is_never_probed(self):
        from apps.osint.enrichers import ssl as ssl_enricher

        with patch("apps.osint.validators.is_public_internet_target", return_value=False), \
             patch("requests.get") as get:
            assert ssl_enricher._serves_over_http("as400.dytech.local") is None
            get.assert_not_called()


# ── Postura attesa dichiarata ────────────────────────────────────────────────

@pytest.mark.django_db
class TestExpectedPosture:
    """La postura dichiarata vince sulla rilevazione; il non dichiarato ricade
    su ciò che si è rilevato (comportamento storico)."""

    def _entity(self, **kw):
        import uuid

        from apps.osint.models import EntityType, OsintEntity, SourceModule

        return OsintEntity.objects.create(
            entity_type=EntityType.MY_DOMAIN,
            source_module=SourceModule.SITES,
            source_id=uuid.uuid4(),
            domain="postura.example.com",
            display_name="Postura",
            **kw,
        )

    def _scan(self, **kw):
        s = MagicMock()
        s.mx_present = kw.get("mx_present", None)
        s.https_available = kw.get("https_available", None)
        s.http_only = kw.get("http_only", None)
        s.ssl_valid = kw.get("ssl_valid", None)
        return s

    def test_declared_no_mail_wins_over_a_detected_mx(self):
        """Un MX rilevato può essere quello del provider che ospita il dominio,
        senza che ci passi la posta aziendale."""
        from apps.osint.models import ExpectedPosture
        from apps.osint.posture import expects_mail

        entity = self._entity(expected_mail=ExpectedPosture.NO)
        assert expects_mail(entity, self._scan(mx_present=True)) is False

    def test_declared_mail_applies_without_an_mx(self):
        """Un dominio usato solo come mittente non ha MX ma deve avere SPF e
        DMARC: è il caso più abusato dal phishing."""
        from apps.osint.models import ExpectedPosture
        from apps.osint.posture import expects_mail

        entity = self._entity(expected_mail=ExpectedPosture.YES)
        assert expects_mail(entity, self._scan(mx_present=False)) is True

    def test_undeclared_falls_back_to_detection(self):
        from apps.osint.posture import expects_mail

        entity = self._entity()
        assert expects_mail(entity, self._scan(mx_present=True)) is True
        assert expects_mail(entity, self._scan(mx_present=False)) is False
        assert expects_mail(entity, self._scan(mx_present=None)) is False

    def test_declared_no_web_silences_the_https_finding(self):
        """Un dominio registrato a scopo difensivo non deve servire nulla:
        segnalarlo perché non ha HTTPS è rumore."""
        from apps.osint.models import ExpectedPosture
        from apps.osint.posture import expects_web

        entity = self._entity(expected_web=ExpectedPosture.NO)
        assert expects_web(entity, self._scan(http_only=True)) is False

    def test_an_expired_certificate_still_counts_as_serving_web(self):
        """Uno scan storico non ha `https_available`: senza questa condizione
        la dimensione SSL verrebbe azzerata su tutto lo storico."""
        from apps.osint.posture import expects_web

        entity = self._entity()
        assert expects_web(entity, self._scan(ssl_valid=False)) is True

    def test_declared_no_mail_zeroes_the_dns_dimension(self):
        from apps.osint.models import ExpectedPosture
        from apps.osint.scoring import _score_dns

        entity = self._entity(expected_mail=ExpectedPosture.NO)
        scan = MagicMock()
        scan.mx_present = True
        scan.spf_present = False
        scan.dmarc_present = False
        scan.spf_policy = ""
        scan.dmarc_policy = ""
        scan.dkim_present = None
        scan.mta_sts_present = None
        assert _score_dns(scan, entity=entity) == 0

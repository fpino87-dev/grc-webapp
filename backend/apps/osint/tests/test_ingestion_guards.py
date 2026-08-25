"""
Validazione dei domini in ingestione.

Censire un hostname che non potrà mai essere scansionato produce un'entità che
resta per sempre senza dati, e nulla lo segnala. Qui si scartano quelle forme,
si evita di monitorare il provider di posta al posto del fornitore, e si
annotano — senza unire nulla — i possibili doppioni www/apex.
"""
import uuid

import pytest

from apps.osint.validators import hostname_is_scannable, is_public_mail_domain

pytestmark = pytest.mark.django_db


class TestHostnameGuard:
    @pytest.mark.parametrize("domain", [
        "as400.dytech.local",
        "chesx.dytech.local",
        "server.internal",
        "host.lan",
        "qualcosa.test",
        "localhost",
        "srv01",              # etichetta singola
        "10.0.0.5",           # IP privato
        "127.0.0.1",
        "",
    ])
    def test_unscannable_hostnames_are_refused(self, domain):
        ok, reason = hostname_is_scannable(domain)
        assert ok is False
        assert reason

    @pytest.mark.parametrize("domain", [
        "sumiriko.it",
        "www.it.sumiriko.com",
        "zucchetti.it",
        "emac.to.it",
    ])
    def test_public_domains_pass(self, domain):
        assert hostname_is_scannable(domain)[0] is True


class TestPublicMailDomains:
    @pytest.mark.parametrize("domain", [
        "gmail.com", "libero.it", "outlook.com", "pec.it", "legalmail.it",
    ])
    def test_provider_domains_are_recognised(self, domain):
        assert is_public_mail_domain(domain) is True

    def test_a_company_domain_is_not_a_provider(self):
        assert is_public_mail_domain("zucchetti.it") is False


class TestSupplierFallback:
    """Il ripiego sull'email non deve far monitorare il provider."""

    def _supplier(self, **kw):
        from apps.suppliers.models import Supplier

        return Supplier.objects.create(
            name=kw.pop("name", "Fornitore Test"),
            status="attivo",
            **kw,
        )

    def test_email_on_a_public_provider_is_not_used(self):
        from apps.osint.models import OsintEntity, SourceModule
        from apps.osint.services import aggregate_entities

        self._supplier(name="Ditta Senza Sito", website="", email="mario@gmail.com")
        aggregate_entities()
        domains = set(
            OsintEntity.objects.filter(source_module=SourceModule.SUPPLIERS)
            .values_list("domain", flat=True)
        )
        assert "gmail.com" not in domains

    def test_email_on_the_company_domain_is_used(self):
        from apps.osint.models import OsintEntity, SourceModule
        from apps.osint.services import aggregate_entities

        self._supplier(name="Ditta Con Dominio", website="", email="info@dittaconsuodominio.it")
        aggregate_entities()
        domains = set(
            OsintEntity.objects.filter(source_module=SourceModule.SUPPLIERS)
            .values_list("domain", flat=True)
        )
        assert "dittaconsuodominio.it" in domains


class TestDuplicateCandidates:
    """`www.X` e `X` sono candidati, non doppioni: si annota il sospetto e non
    si unisce nulla d'ufficio."""

    def _entity(self, domain):
        from apps.osint.models import EntityType, OsintEntity, SourceModule

        return OsintEntity.objects.create(
            entity_type=EntityType.MY_DOMAIN,
            source_module=SourceModule.SITES,
            source_id=uuid.uuid4(),
            domain=domain,
            display_name=domain,
        )

    def test_www_and_apex_are_flagged_as_candidates(self):
        from apps.osint.services import _mark_duplicate_candidate

        apex = self._entity("esempio.it")
        www = self._entity("www.esempio.it")
        _mark_duplicate_candidate(www)

        www.refresh_from_db()
        assert www.duplicate_candidate_of_id == apex.pk
        assert www.duplicate_verified is None, "il sospetto non è ancora una verifica"

    def test_neither_entity_is_removed_or_deactivated(self):
        from apps.osint.services import _mark_duplicate_candidate

        apex = self._entity("esempio.it")
        www = self._entity("www.esempio.it")
        _mark_duplicate_candidate(www)

        apex.refresh_from_db()
        www.refresh_from_db()
        assert apex.is_active and www.is_active

    def test_a_subdomain_has_no_counterpart(self):
        """`api.esempio.it` non ha una controparte www plausibile."""
        from apps.osint.services import _counterpart_domain

        assert _counterpart_domain("api.esempio.it") == ""
        assert _counterpart_domain("esempio.it") == "www.esempio.it"
        assert _counterpart_domain("www.esempio.it") == "esempio.it"

    def test_same_addresses_confirm_the_alias(self):
        from unittest.mock import patch

        from apps.osint.services import _mark_duplicate_candidate, verify_duplicate_candidate

        self._entity("esempio.it")
        www = self._entity("www.esempio.it")
        _mark_duplicate_candidate(www)

        with patch("apps.osint.validators._resolve_all", return_value=["93.184.216.34"]):
            assert verify_duplicate_candidate(www) is True

    def test_different_addresses_prove_they_are_distinct(self):
        """Il caso che vieta l'unione automatica: stesso nome, host diversi."""
        from unittest.mock import patch

        from apps.osint.services import _mark_duplicate_candidate, verify_duplicate_candidate

        self._entity("esempio.it")
        www = self._entity("www.esempio.it")
        _mark_duplicate_candidate(www)

        with patch("apps.osint.validators._resolve_all", side_effect=[["1.1.1.1"], ["2.2.2.2"]]):
            assert verify_duplicate_candidate(www) is False

    def test_unresolvable_leaves_the_doubt_open(self):
        from unittest.mock import patch

        from apps.osint.services import _mark_duplicate_candidate, verify_duplicate_candidate

        self._entity("esempio.it")
        www = self._entity("www.esempio.it")
        _mark_duplicate_candidate(www)

        with patch("apps.osint.validators._resolve_all", return_value=[]):
            assert verify_duplicate_candidate(www) is None


class TestPostureEndpoint:
    """La postura è l'unico campo scrivibile su un'entità: tutto il resto
    specchia il modulo di origine."""

    def _client(self):
        from apps.auth_grc.models import GrcRole, UserPlantAccess
        from django.contrib.auth import get_user_model
        from rest_framework.test import APIClient

        User = get_user_model()
        u = User.objects.create_user(
            username="osint@test.com", email="osint@test.com", password="x"
        )
        UserPlantAccess.objects.create(
            user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org"
        )
        c = APIClient()
        c.force_authenticate(user=u)
        return c

    def _entity(self):
        from apps.osint.models import EntityType, OsintEntity, SourceModule

        return OsintEntity.objects.create(
            entity_type=EntityType.MY_DOMAIN,
            source_module=SourceModule.SITES,
            source_id=uuid.uuid4(),
            domain="dichiarato.example.com",
            display_name="Dichiarato",
        )

    def test_declaring_the_posture(self):
        entity = self._entity()
        resp = self._client().patch(
            f"/api/v1/osint/entities/{entity.id}/posture/",
            {"expected_mail": "no", "expected_web": "yes"},
            format="json",
        )
        assert resp.status_code == 200, resp.data
        entity.refresh_from_db()
        assert entity.expected_mail == "no"
        assert entity.expected_web == "yes"

    def test_the_declaration_is_audited(self):
        from core.audit import AuditLog

        entity = self._entity()
        self._client().patch(
            f"/api/v1/osint/entities/{entity.id}/posture/",
            {"expected_mail": "no"},
            format="json",
        )
        assert AuditLog.objects.filter(action_code="osint.posture_declared").exists()

    def test_other_fields_stay_read_only(self):
        """Il dominio specchia la sorgente: non si cambia da qui."""
        entity = self._entity()
        self._client().patch(
            f"/api/v1/osint/entities/{entity.id}/posture/",
            {"expected_mail": "no", "domain": "dirottato.example.com"},
            format="json",
        )
        entity.refresh_from_db()
        assert entity.domain == "dichiarato.example.com"

    def test_an_invalid_value_is_refused(self):
        entity = self._entity()
        resp = self._client().patch(
            f"/api/v1/osint/entities/{entity.id}/posture/",
            {"expected_mail": "forse"},
            format="json",
        )
        assert resp.status_code == 400

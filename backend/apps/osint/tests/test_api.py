"""Test Step 8 — API REST OSINT."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.osint.models import (
    AlertSeverity, AlertStatus, AlertType,
    EntityType, OsintAlert, OsintEntity, OsintSettings, OsintSubdomain,
    ScanStatus, SourceModule, SubdomainStatus,
)
from apps.plants.models import Plant

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def user(db):
    # Superuser: bypassa OsintReadPermission/OsintWritePermission senza dover
    # creare un UserPlantAccess. Per i test API è sufficiente.
    return User.objects.create_superuser(username="osintuser", password="testpass", email="o@test.com")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def plant(db):
    return Plant.objects.create(
        code="API1", name="API Plant", country="IT",
        nis2_scope="essenziale", status="attivo",
        domain="apitest.example.com",
    )


@pytest.fixture
def entity(plant):
    return OsintEntity.objects.create(
        entity_type=EntityType.MY_DOMAIN,
        source_module=SourceModule.SITES,
        source_id=plant.id,
        domain="apitest.example.com",
        display_name="API Plant",
    )


@pytest.fixture
def scan(entity):
    from apps.osint.models import OsintScan
    return OsintScan.objects.create(
        entity=entity, status=ScanStatus.COMPLETED,
        score_total=75, score_ssl=100, score_dns=50,
        score_reputation=10, score_grc_context=20,
    )


@pytest.fixture
def alert(entity, scan):
    return OsintAlert.objects.create(
        entity=entity, scan=scan,
        alert_type=AlertType.SSL_EXPIRED,
        severity=AlertSeverity.CRITICAL,
        description="SSL scaduto",
        status=AlertStatus.NEW,
    )


class TestEntityAPI:
    def test_list_entities(self, auth_client, entity):
        resp = auth_client.get("/api/v1/osint/entities/")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_retrieve_entity(self, auth_client, entity):
        resp = auth_client.get(f"/api/v1/osint/entities/{entity.id}/")
        assert resp.status_code == 200
        assert resp.json()["domain"] == "apitest.example.com"

    def test_entity_history(self, auth_client, entity, scan):
        resp = auth_client.get(f"/api/v1/osint/entities/{entity.id}/history/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["score_total"] == 75

    def test_force_scan_queued(self, auth_client, entity):
        from unittest.mock import patch
        with patch("apps.osint.tasks.run_entity_scan.delay") as mock_delay:
            mock_job = type("Job", (), {"id": "fake-job-id"})()
            mock_delay.return_value = mock_job
            resp = auth_client.post(f"/api/v1/osint/entities/{entity.id}/scan/")
        assert resp.status_code == 202
        assert resp.json()["status"] == "queued"

    def test_filter_by_type(self, auth_client, entity):
        resp = auth_client.get("/api/v1/osint/entities/?entity_type=my_domain")
        assert resp.status_code == 200

    def test_unauthenticated_blocked(self):
        client = APIClient()
        resp = client.get("/api/v1/osint/entities/")
        assert resp.status_code == 401


class TestEntityAPI2:
    def test_search_by_domain(self, auth_client, entity):
        resp = auth_client.get("/api/v1/osint/entities/?search=apitest")
        assert resp.status_code == 200
        assert any(e["domain"] == "apitest.example.com" for e in resp.json())

    def test_search_no_match(self, auth_client, entity):
        resp = auth_client.get("/api/v1/osint/entities/?search=notexist99")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_force_scan_404(self, auth_client):
        resp = auth_client.post("/api/v1/osint/entities/00000000-0000-0000-0000-000000000000/scan/")
        assert resp.status_code == 404

    def test_detail_has_active_alerts(self, auth_client, entity, alert):
        resp = auth_client.get(f"/api/v1/osint/entities/{entity.id}/")
        assert resp.status_code == 200
        data = resp.json()
        assert "active_alerts" in data
        assert len(data["active_alerts"]) == 1
        assert data["active_alerts"][0]["alert_type"] == "ssl_expired"

    def test_history_empty_without_scan(self, auth_client, entity):
        resp = auth_client.get(f"/api/v1/osint/entities/{entity.id}/history/")
        assert resp.status_code == 200
        assert resp.json() == []


class TestAlertAPI:
    def test_list_alerts(self, auth_client, alert):
        resp = auth_client.get("/api/v1/osint/alerts/")
        assert resp.status_code == 200
        assert any(str(alert.id) == a["id"] for a in resp.json())

    def test_acknowledge_alert(self, auth_client, alert):
        resp = auth_client.patch(
            f"/api/v1/osint/alerts/{alert.id}/",
            {"status": "acknowledged"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "acknowledged"

    def test_resolve_alert(self, auth_client, alert):
        resp = auth_client.patch(
            f"/api/v1/osint/alerts/{alert.id}/",
            {"status": "resolved"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved"
        assert resp.json()["resolved_at"] is not None

    def test_invalid_status(self, auth_client, alert):
        resp = auth_client.patch(
            f"/api/v1/osint/alerts/{alert.id}/",
            {"status": "new"},
            format="json",
        )
        assert resp.status_code == 400

    def test_filter_by_severity(self, auth_client, alert):
        resp = auth_client.get("/api/v1/osint/alerts/?severity=critical")
        assert resp.status_code == 200
        assert all(a["severity"] == "critical" for a in resp.json())

    def test_filter_by_status(self, auth_client, alert):
        resp = auth_client.get("/api/v1/osint/alerts/?status=new")
        assert resp.status_code == 200
        assert any(str(alert.id) == a["id"] for a in resp.json())

    def test_escalate_ignore(self, auth_client, entity):
        pending_alert = OsintAlert.objects.create(
            entity=entity,
            alert_type=AlertType.NEW_SUBDOMAIN,
            severity=AlertSeverity.WARNING,
            description="Nuovo sottodominio",
            status=AlertStatus.PENDING_ESCALATION,
        )
        resp = auth_client.post(
            f"/api/v1/osint/alerts/{pending_alert.id}/escalate/",
            {"action": "ignore"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved"

    def test_escalate_invalid_action(self, auth_client, entity):
        pending_alert = OsintAlert.objects.create(
            entity=entity,
            alert_type=AlertType.NEW_SUBDOMAIN,
            severity=AlertSeverity.WARNING,
            description="test",
            status=AlertStatus.PENDING_ESCALATION,
        )
        resp = auth_client.post(
            f"/api/v1/osint/alerts/{pending_alert.id}/escalate/",
            {"action": "delete"},
            format="json",
        )
        assert resp.status_code == 400

    def test_escalate_non_pending_returns_404(self, auth_client, alert):
        resp = auth_client.post(
            f"/api/v1/osint/alerts/{alert.id}/escalate/",
            {"action": "ignore"},
            format="json",
        )
        assert resp.status_code == 404


class TestSubdomainAPI:
    def test_pending_subdomains(self, auth_client, entity):
        sub = OsintSubdomain.objects.create(
            entity=entity, subdomain="sub.apitest.example.com",
            status=SubdomainStatus.PENDING,
        )
        resp = auth_client.get("/api/v1/osint/subdomains/pending/")
        assert resp.status_code == 200
        assert any(s["subdomain"] == "sub.apitest.example.com" for s in resp.json())

    def test_classify_subdomain(self, auth_client, entity):
        sub = OsintSubdomain.objects.create(
            entity=entity, subdomain="x.apitest.example.com",
            status=SubdomainStatus.PENDING,
        )
        resp = auth_client.patch(
            f"/api/v1/osint/subdomains/{sub.id}/",
            {"status": "included"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "included"

    def test_classify_subdomain_ignored(self, auth_client, entity):
        sub = OsintSubdomain.objects.create(
            entity=entity, subdomain="y.apitest.example.com",
            status=SubdomainStatus.PENDING,
        )
        resp = auth_client.patch(
            f"/api/v1/osint/subdomains/{sub.id}/",
            {"status": "ignored"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    def test_classify_invalid_status(self, auth_client, entity):
        sub = OsintSubdomain.objects.create(
            entity=entity, subdomain="z.apitest.example.com",
            status=SubdomainStatus.PENDING,
        )
        resp = auth_client.patch(
            f"/api/v1/osint/subdomains/{sub.id}/",
            {"status": "not_a_real_status"},
            format="json",
        )
        assert resp.status_code == 400

    def test_included_subdomain_not_in_pending(self, auth_client, entity):
        OsintSubdomain.objects.create(
            entity=entity, subdomain="included.apitest.example.com",
            status=SubdomainStatus.INCLUDED,
        )
        resp = auth_client.get("/api/v1/osint/subdomains/pending/")
        assert resp.status_code == 200
        assert not any(s["subdomain"] == "included.apitest.example.com" for s in resp.json())


class TestDashboardAPI:
    def test_summary(self, auth_client, entity, scan):
        resp = auth_client.get("/api/v1/osint/dashboard/summary/")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_entities" in data
        assert "critical_count" in data
        assert "pending_subdomains" in data

    def test_summary_critical_count(self, auth_client, entity, scan):
        # scan ha score_total=75 ≥ soglia critica default 70
        resp = auth_client.get("/api/v1/osint/dashboard/summary/")
        data = resp.json()
        assert data["critical_count"] >= 1

    def test_summary_counts_pending_subdomains(self, auth_client, entity, scan):
        OsintSubdomain.objects.create(
            entity=entity, subdomain="pending.apitest.example.com",
            status=SubdomainStatus.PENDING,
        )
        resp = auth_client.get("/api/v1/osint/dashboard/summary/")
        assert resp.json()["pending_subdomains"] >= 1


class TestSettingsAPI:
    def test_get_settings(self, auth_client):
        resp = auth_client.get("/api/v1/osint/settings/")
        assert resp.status_code == 200
        data = resp.json()
        assert "score_threshold_critical" in data
        assert data["score_threshold_critical"] == 70

    def test_patch_settings(self, auth_client):
        resp = auth_client.patch(
            "/api/v1/osint/settings/",
            {"score_threshold_critical": 80},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["score_threshold_critical"] == 80

    def test_api_key_write_only(self, auth_client):
        auth_client.patch("/api/v1/osint/settings/", {"hibp_api_key": "secret"}, format="json")
        resp = auth_client.get("/api/v1/osint/settings/")
        assert "hibp_api_key" not in resp.json()
        assert resp.json()["has_hibp_key"] is True

    def test_patch_warning_threshold(self, auth_client):
        resp = auth_client.patch(
            "/api/v1/osint/settings/",
            {"score_threshold_warning": 40},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["score_threshold_warning"] == 40

    def test_patch_subdomain_policy(self, auth_client):
        for policy in ("yes", "no", "ask"):
            resp = auth_client.patch(
                "/api/v1/osint/settings/",
                {"subdomain_auto_include": policy},
                format="json",
            )
            assert resp.status_code == 200
            assert resp.json()["subdomain_auto_include"] == policy

    def test_patch_anonymization_toggle(self, auth_client):
        resp = auth_client.patch(
            "/api/v1/osint/settings/",
            {"anonymization_enabled": False},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["anonymization_enabled"] is False


class TestAggregatorEmailFallback:
    def test_supplier_domain_from_email(self, db):
        from apps.osint.services import domain_from_email, aggregate_entities
        from apps.suppliers.models import Supplier

        sup = Supplier.objects.create(
            name="Test Supplier",
            email="contact@smeup.com",
            website="",
            risk_level="basso",
            status="attivo",
        )
        result = aggregate_entities()
        from apps.osint.models import OsintEntity
        entity = OsintEntity.objects.filter(source_id=sup.id).first()
        assert entity is not None
        assert entity.domain == "smeup.com"

    def test_domain_from_email_helper(self):
        from apps.osint.services import domain_from_email
        assert domain_from_email("user@example.com") == "example.com"
        assert domain_from_email("USER@EXAMPLE.COM") == "example.com"
        assert domain_from_email("") == ""
        assert domain_from_email(None) == ""
        assert domain_from_email("notanemail") == ""

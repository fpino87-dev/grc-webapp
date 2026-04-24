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
    return User.objects.create_user(username="osintuser", password="testpass", email="o@test.com")


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


class TestDashboardAPI:
    def test_summary(self, auth_client, entity, scan):
        resp = auth_client.get("/api/v1/osint/dashboard/summary/")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_entities" in data
        assert "critical_count" in data
        assert "pending_subdomains" in data


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

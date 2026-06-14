"""Test API config provider AI (M20 review): api_key non esposta + audit."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL = "/api/v1/ai/config/"


@pytest.fixture
def admin_client(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="ai_sa", email="ai_sa@test.com", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.SUPER_ADMIN, scope_type="org")
    c = APIClient()
    c.force_authenticate(user=u)
    return c


def _audit_count(event):
    from core.audit import AuditLog
    return AuditLog.objects.filter(action_code="ai.config.changed", payload__event=event).count()


@pytest.mark.django_db
def test_create_config_does_not_echo_api_key_and_is_audited(admin_client):
    before = _audit_count("created")
    resp = admin_client.post(
        URL,
        {"name": "Test", "cloud_provider": "anthropic", "api_key": "sk-secret-123"},
        format="json",
    )
    assert resp.status_code == 201
    # la chiave non torna nella risposta (write_only)
    assert "api_key" not in resp.data or resp.data.get("api_key") in (None, "")
    assert "sk-secret-123" not in str(resp.data)
    assert _audit_count("created") == before + 1


@pytest.mark.django_db
def test_get_config_masks_api_key(admin_client):
    from apps.ai_engine.models import AiProviderConfig
    cfg = AiProviderConfig.objects.create(name="C", cloud_provider="anthropic", api_key="sk-zzz")
    resp = admin_client.get(f"{URL}{cfg.id}/")
    assert resp.status_code == 200
    assert resp.data["api_key"] == "********"
    assert "sk-zzz" not in str(resp.data)


@pytest.mark.django_db
def test_destroy_config_is_soft_and_audited(admin_client):
    from apps.ai_engine.models import AiProviderConfig
    cfg = AiProviderConfig.objects.create(name="C", cloud_provider="anthropic")
    before = _audit_count("deleted")
    resp = admin_client.delete(f"{URL}{cfg.id}/")
    assert resp.status_code == 204
    cfg.refresh_from_db()
    assert cfg.deleted_at is not None
    assert AiProviderConfig.objects.filter(pk=cfg.pk).count() == 0
    assert AiProviderConfig.objects.all_with_deleted().filter(pk=cfg.pk).count() == 1
    assert _audit_count("deleted") == before + 1

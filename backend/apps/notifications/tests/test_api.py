"""Test API notifiche: audit sul routing (regole/profili) — M19 review."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_RULES = "/api/v1/notifications/rules/"
URL_PROFILES = "/api/v1/notifications/role-profiles/"


@pytest.fixture
def admin_client(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="notif_sa", email="notif_sa@test.com", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.SUPER_ADMIN, scope_type="org")
    c = APIClient()
    c.force_authenticate(user=u)
    return c


def _audit_count(action_code, event):
    from core.audit import AuditLog
    return AuditLog.objects.filter(action_code=action_code, payload__event=event).count()


@pytest.mark.django_db
def test_rule_delete_is_audited(admin_client):
    from apps.notifications.models import NotificationRule
    rule = NotificationRule.objects.create(event_type="osint_critical", scope_type="org")
    before = _audit_count("notif.smtp.config.changed", "rule_deleted")
    resp = admin_client.delete(f"{URL_RULES}{rule.id}/")
    assert resp.status_code == 204
    assert _audit_count("notif.smtp.config.changed", "rule_deleted") == before + 1
    assert not NotificationRule.objects.filter(pk=rule.id).exists()


@pytest.mark.django_db
def test_role_profile_set_custom_is_audited(admin_client):
    from apps.notifications.models import NotificationRoleProfile
    prof = NotificationRoleProfile.objects.create(grc_role="risk_manager", profile="standard")
    before = _audit_count("notif.profile.changed", "profile_set_custom")
    resp = admin_client.post(
        f"{URL_PROFILES}{prof.id}/set-custom/",
        {"events": ["osint_critical"]},
        format="json",
    )
    assert resp.status_code == 200
    assert _audit_count("notif.profile.changed", "profile_set_custom") == before + 1

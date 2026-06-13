"""Review prod-readiness M02 (2026-06-13) — CRITICAL privilege escalation.

`UserPlantAccessViewSet` ed `ExternalAuditorTokenViewSet` non avevano
`permission_classes`: ricadevano sul default DRF `IsAuthenticated`, quindi un
qualsiasi utente autenticato poteva creare una `UserPlantAccess` con
role=super_admin/scope=org (la tabella RBAC reale letta dal JWT) e
auto-promuoversi, o emettere token di accesso per auditor esterni.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.auth_grc.models import GrcRole, UserPlantAccess

User = get_user_model()

URL_ACCESS = "/api/v1/auth/plant-access/"
URL_TOKENS = "/api/v1/auth/auditor-tokens/"
URL_COMP_REQ = "/api/v1/auth/competency-requirements/"


def _client(role=None, *, superuser=False, no_role=False):
    safe = (role or "norole").replace("_", "")
    u = User.objects.create_user(username=f"m2_{safe}", email=f"{safe}@m2.test", password="x")
    if superuser:
        u.is_superuser = True
        u.is_staff = True
        u.save()
    if role and not no_role:
        UserPlantAccess.objects.create(user=u, role=role, scope_type="org")
    c = APIClient()
    c.force_authenticate(user=u)
    return c, u


@pytest.mark.django_db
def test_non_admin_cannot_self_grant_super_admin():
    """Il cuore della vuln: un control_owner non può crearsi un accesso super_admin."""
    client, user = _client(GrcRole.CONTROL_OWNER)
    before = UserPlantAccess.objects.filter(user=user, role=GrcRole.SUPER_ADMIN).count()
    resp = client.post(URL_ACCESS, {
        "user": user.id, "role": GrcRole.SUPER_ADMIN, "scope_type": "org",
    }, format="json")
    assert resp.status_code == 403, resp.status_code
    assert UserPlantAccess.objects.filter(user=user, role=GrcRole.SUPER_ADMIN).count() == before


@pytest.mark.django_db
def test_no_role_user_cannot_grant_access():
    client, user = _client(no_role=True)
    resp = client.post(URL_ACCESS, {
        "user": user.id, "role": GrcRole.SUPER_ADMIN, "scope_type": "org",
    }, format="json")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_compliance_officer_cannot_grant_access():
    """Anche un compliance_officer (ruolo alto ma non super admin) non gestisce
    la tabella RBAC reale: è operazione da super admin."""
    client, _ = _client(GrcRole.COMPLIANCE_OFFICER)
    assert client.get(URL_ACCESS).status_code == 403


@pytest.mark.django_db
def test_super_admin_can_manage_access():
    client, _ = _client(GrcRole.SUPER_ADMIN)
    # passa il permesso (lettura 200); la POST con payload minimo non è 403
    assert client.get(URL_ACCESS).status_code == 200
    assert client.post(URL_ACCESS, {}, format="json").status_code != 403


@pytest.mark.django_db
def test_django_superuser_can_manage_access():
    client, _ = _client(superuser=True)
    assert client.get(URL_ACCESS).status_code == 200


@pytest.mark.django_db
def test_non_admin_cannot_issue_auditor_token():
    client, _ = _client(GrcRole.CONTROL_OWNER)
    assert client.get(URL_TOKENS).status_code == 403
    assert client.post(URL_TOKENS, {}, format="json").status_code == 403


@pytest.mark.django_db
def test_competency_requirement_read_ok_write_restricted():
    client, _ = _client(GrcRole.CONTROL_OWNER)
    assert client.get(URL_COMP_REQ).status_code == 200          # lettura per i ruoli GRC
    assert client.post(URL_COMP_REQ, {}, format="json").status_code == 403  # config negata


URL_USERS = "/api/v1/auth/users/"


@pytest.mark.django_db
def test_admin_create_user_enforces_password_policy():
    client, _ = _client(GrcRole.SUPER_ADMIN)
    weak = client.post(URL_USERS, {
        "username": "weak1", "email": "weak1@m2.test", "password": "short",
    }, format="json")
    assert weak.status_code == 400
    assert "password" in weak.data
    strong = client.post(URL_USERS, {
        "username": "strong1", "email": "strong1@m2.test", "password": "Corret7Horse!Battery",
    }, format="json")
    assert strong.status_code == 201


@pytest.mark.django_db
def test_set_password_enforces_policy_and_audits():
    from core.audit import AuditLog
    client, _ = _client(GrcRole.SUPER_ADMIN)
    target = User.objects.create_user(username="pwtarget", email="pwt@m2.test", password="x")
    assert client.post(f"{URL_USERS}{target.id}/set_password/", {"password": "abc"}, format="json").status_code == 400
    ok = client.post(f"{URL_USERS}{target.id}/set_password/", {"password": "Corret7Horse!Battery"}, format="json")
    assert ok.status_code == 200
    assert AuditLog.objects.filter(action_code="auth.user.password_reset").exists()


@pytest.mark.django_db
def test_assign_role_soft_deletes_old_and_audits():
    from core.audit import AuditLog
    client, _ = _client(GrcRole.SUPER_ADMIN)
    target = User.objects.create_user(username="rtarget", email="rt@m2.test", password="x")
    old = UserPlantAccess.objects.create(user=target, role=GrcRole.CONTROL_OWNER, scope_type="org")
    resp = client.post(f"{URL_USERS}{target.id}/assign_role/",
                       {"role": GrcRole.PLANT_MANAGER, "scope_type": "org"}, format="json")
    assert resp.status_code == 200
    old.refresh_from_db()
    assert old.deleted_at is not None  # soft delete, non hard delete
    assert UserPlantAccess.objects.filter(user=target, role=GrcRole.PLANT_MANAGER).exists()
    assert AuditLog.objects.filter(action_code="auth.access.granted").exists()

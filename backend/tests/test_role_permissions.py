"""Test della classe `RoleScopedPermission` (newfix F1).

Coprono il contratto cardinale:
- l'utente non autenticato → 401/403
- l'utente autenticato senza alcun `UserPlantAccess` → 403 su read e write
- l'utente con ruolo presente solo in `read_roles` → 200 su GET, 403 su POST/PUT/DELETE
- l'utente con ruolo presente in `write_roles` → 200/201 anche su scrittura
- il superuser → bypass
- la verifica e' fatta indipendentemente dal modulo (tre endpoint disjoint:
  incidents/RBAC operativo, audit_prep/RBAC auditor, suppliers/RBAC governance)
  per assicurarsi che il wiring sia in place su ogni ViewSet.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


def _grant(user, role, *, scope_type="org"):
    from apps.auth_grc.models import UserPlantAccess
    return UserPlantAccess.objects.create(
        user=user, role=role, scope_type=scope_type,
    )


def _client(user=None):
    c = APIClient()
    if user is not None:
        c.force_authenticate(user=user)
    return c


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="RP-1", name="Plant RP", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def no_role_user(db):
    return User.objects.create_user(username="no_role", email="no_role@t.com", password="x")


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(username="su", email="su@t.com", password="x")


# ── Incidents (operativi: super_admin, compliance_officer, risk_manager,
#               plant_manager + auditor read-only) ────────────────────────

URL_INCIDENTS = "/api/v1/incidents/incidents/"


@pytest.mark.django_db
def test_incidents_unauthenticated_blocked():
    resp = _client().get(URL_INCIDENTS)
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_incidents_no_role_blocked(no_role_user):
    resp = _client(no_role_user).get(URL_INCIDENTS)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_incidents_external_auditor_can_read_not_write(db, plant):
    from apps.auth_grc.models import GrcRole
    u = User.objects.create_user(username="ext_aud", email="ea@t.com", password="x")
    _grant(u, GrcRole.EXTERNAL_AUDITOR)
    c = _client(u)
    assert c.get(URL_INCIDENTS).status_code == 200
    payload = {"plant": str(plant.id), "title": "x", "description": "d", "severity": "bassa"}
    assert c.post(URL_INCIDENTS, payload, format="json").status_code == 403


@pytest.mark.django_db
def test_incidents_risk_manager_can_write(db, plant):
    from apps.auth_grc.models import GrcRole
    u = User.objects.create_user(username="rm_inc", email="rm_inc@t.com", password="x")
    _grant(u, GrcRole.RISK_MANAGER)
    c = _client(u)
    payload = {"plant": str(plant.id), "title": "x", "description": "d", "severity": "bassa"}
    resp = c.post(URL_INCIDENTS, payload, format="json")
    # importante: NON 403; un eventuale 400 di validazione e' acettabile (la
    # permission e' passata, e' la validazione del serializer che decide)
    assert resp.status_code != 403


@pytest.mark.django_db
def test_incidents_superuser_bypass(db, superuser, plant):
    c = _client(superuser)
    assert c.get(URL_INCIDENTS).status_code == 200


# ── Audit Prep (RBAC auditor: read = +external_auditor, write = solo
#                super_admin/compliance_officer/internal_auditor) ────────

URL_AUDIT_PREP = "/api/v1/audit-prep/audit-preps/"


@pytest.mark.django_db
def test_audit_prep_no_role_blocked(no_role_user):
    resp = _client(no_role_user).get(URL_AUDIT_PREP)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_audit_prep_plant_manager_blocked(db):
    from apps.auth_grc.models import GrcRole
    u = User.objects.create_user(username="pm_ap", email="pm_ap@t.com", password="x")
    _grant(u, GrcRole.PLANT_MANAGER)
    # plant_manager non e' nel set _AUDITOR_PLUS → niente lettura
    assert _client(u).get(URL_AUDIT_PREP).status_code == 403


@pytest.mark.django_db
def test_audit_prep_external_auditor_read_only(db):
    from apps.auth_grc.models import GrcRole
    u = User.objects.create_user(username="ea_ap", email="ea_ap@t.com", password="x")
    _grant(u, GrcRole.EXTERNAL_AUDITOR)
    c = _client(u)
    assert c.get(URL_AUDIT_PREP).status_code == 200
    # external_auditor non puo' scrivere (osservatore)
    resp = c.post(URL_AUDIT_PREP, {}, format="json")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_audit_prep_internal_auditor_can_write(db, plant):
    from apps.auth_grc.models import GrcRole
    u = User.objects.create_user(username="ia_ap", email="ia_ap@t.com", password="x")
    _grant(u, GrcRole.INTERNAL_AUDITOR)
    c = _client(u)
    # read OK
    assert c.get(URL_AUDIT_PREP).status_code == 200
    # write tentativo (anche con payload vuoto deve passare il controllo permission;
    # il 400 di validazione e' accettabile, l'importante e' che NON sia 403)
    resp = c.post(URL_AUDIT_PREP, {}, format="json")
    assert resp.status_code != 403


# ── Suppliers (governance: super_admin/compliance_officer/risk_manager/
#               plant_manager + auditor read-only) ──────────────────────

URL_SUPPLIERS = "/api/v1/suppliers/suppliers/"


@pytest.mark.django_db
def test_suppliers_no_role_blocked(no_role_user):
    assert _client(no_role_user).get(URL_SUPPLIERS).status_code == 403


@pytest.mark.django_db
def test_suppliers_external_auditor_read_only(db):
    from apps.auth_grc.models import GrcRole
    u = User.objects.create_user(username="ea_sup", email="ea_sup@t.com", password="x")
    _grant(u, GrcRole.EXTERNAL_AUDITOR)
    c = _client(u)
    assert c.get(URL_SUPPLIERS).status_code == 200
    payload = {"name": "Acme", "vat_number": "00000000000"}
    assert c.post(URL_SUPPLIERS, payload, format="json").status_code == 403


@pytest.mark.django_db
def test_suppliers_compliance_officer_can_write(db):
    from apps.auth_grc.models import GrcRole
    u = User.objects.create_user(username="co_sup", email="co_sup@t.com", password="x")
    _grant(u, GrcRole.COMPLIANCE_OFFICER)
    c = _client(u)
    payload = {"name": "Acme", "vat_number": "11111111111"}
    resp = c.post(URL_SUPPLIERS, payload, format="json")
    assert resp.status_code in (201, 200)


# ── Helper user_has_any_role: contratti edge ────────────────────────────


@pytest.mark.django_db
def test_user_has_any_role_unauthenticated_returns_false():
    from core.permissions import user_has_any_role
    from apps.auth_grc.models import GrcRole
    assert user_has_any_role(None, [GrcRole.SUPER_ADMIN]) is False


@pytest.mark.django_db
def test_user_has_any_role_soft_deleted_access_excluded(db):
    from apps.auth_grc.models import GrcRole
    from core.permissions import user_has_any_role
    u = User.objects.create_user(username="del_acc", email="da@t.com", password="x")
    access = _grant(u, GrcRole.RISK_MANAGER)
    access.soft_delete()
    assert user_has_any_role(u, [GrcRole.RISK_MANAGER]) is False


@pytest.mark.django_db
def test_user_has_any_role_empty_allowed_returns_false(db, no_role_user):
    from core.permissions import user_has_any_role
    assert user_has_any_role(no_role_user, []) is False

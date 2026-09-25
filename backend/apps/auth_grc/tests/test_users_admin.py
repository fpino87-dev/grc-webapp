"""Gestione utenti ripensata: elenco con accessi descritti, responsabilità,
avvisi di coerenza, disattivati; creazione con accessi; matrice dei ruoli."""
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.auth_grc.models import GrcRole, UserPlantAccess

from . import test_access_management as base

admin_client, topo = base.admin_client, base.topo

User = get_user_model()
URL = "/api/v1/auth/users/"


def _row(resp, username):
    return next(u for u in resp.data["results"] if u["username"] == username)


@pytest.mark.django_db
def test_list_describes_accesses_and_responsibility_gaps(admin_client, topo):
    from apps.governance.models import NormativeRole, RoleAssignment
    pa, pb, target = topo
    acc = UserPlantAccess.objects.create(user=target, role=GrcRole.CONTROL_OWNER, scope_type="single_plant")
    acc.scope_plants.set([pa])
    RoleAssignment.objects.create(user=target, role=NormativeRole.DPO, scope_type="plant", scope_id=pb.id,
                                  valid_from=timezone.localdate())
    RoleAssignment.objects.create(user=target, role=NormativeRole.CISO, scope_type="plant", scope_id=pa.id,
                                  valid_from=timezone.localdate() - datetime.timedelta(days=30),
                                  valid_until=timezone.localdate() - datetime.timedelta(days=1))
    row = _row(admin_client.get(URL), "f2target")
    assert row["accesses"][0]["scope_plant_codes"] == ["F2A"]
    assert row["accesses"][0]["role"] == "control_owner"
    assert [r["role"] for r in row["responsibilities"]] == ["dpo"]  # la scaduta no
    assert row["responsibilities"][0]["scope_code"] == "F2B"
    assert [w["role"] for w in row["warnings"]] == ["dpo"]  # DPO su F2B senza accesso
    assert row["mfa_enabled"] is False and "last_login" in row


@pytest.mark.django_db
def test_bu_access_covers_bu_responsibility(admin_client, topo):
    from apps.governance.models import NormativeRole, RoleAssignment
    pa, pb, target = topo
    UserPlantAccess.objects.create(user=target, role=GrcRole.PLANT_MANAGER, scope_type="bu", scope_bu=pa.bu)
    RoleAssignment.objects.create(user=target, role=NormativeRole.BU_REFERENTE, scope_type="bu",
                                  scope_id=pa.bu_id, valid_from=timezone.localdate())
    assert _row(admin_client.get(URL), "f2target")["warnings"] == []


@pytest.mark.django_db
def test_inactive_users_listed_on_request_and_reactivated(admin_client, topo):
    pa, pb, target = topo
    target.is_active = False
    target.save()
    assert "f2target" not in [u["username"] for u in admin_client.get(URL).data["results"]]
    assert [u["username"] for u in admin_client.get(URL, {"status": "inactive"}).data["results"]] == ["f2target"]
    resp = admin_client.post(f"{URL}{target.id}/toggle_active/")
    assert resp.status_code == 200 and resp.data["is_active"] is True


@pytest.mark.django_db
def test_create_user_with_site_accesses(admin_client, topo):
    from core.scoping import get_user_plant_ids
    pa, pb, target = topo
    resp = admin_client.post(URL, {
        "username": "nuovo", "email": "nuovo@a.test", "password": "Una-Password-Lunga-2026",
        "accesses": [{"role": "risk_manager", "scope_type": "plant_list", "scope_plants": [str(pa.id), str(pb.id)]}],
    }, format="json")
    assert resp.status_code == 201, resp.data
    u = User.objects.get(username="nuovo")
    assert get_user_plant_ids(u) == {pa.id, pb.id}


@pytest.mark.django_db
def test_create_user_with_invalid_access_is_atomic(admin_client, topo):
    resp = admin_client.post(URL, {
        "username": "vuoto", "email": "vuoto@a.test", "password": "Una-Password-Lunga-2026",
        "accesses": [{"role": "risk_manager", "scope_type": "plant_list"}],
    }, format="json")
    assert resp.status_code == 400
    assert not User.objects.filter(username="vuoto").exists()


@pytest.mark.django_db
def test_user_list_query_count_is_bounded(admin_client, topo, django_assert_max_num_queries):
    pa, pb, target = topo
    for i in range(6):
        u = User.objects.create_user(username=f"bulk{i}", email=f"b{i}@a.test", password="x")
        a = UserPlantAccess.objects.create(user=u, role=GrcRole.CONTROL_OWNER, scope_type="plant_list")
        a.scope_plants.set([pa, pb])
    with django_assert_max_num_queries(20):
        admin_client.get(URL)


@pytest.mark.django_db
def test_role_matrix_reads_permission_classes(admin_client):
    data = admin_client.get(f"{URL}role-matrix/").data
    assert set(data["roles"]) == {r.value for r in GrcRole}
    pdca = next(a for a in data["areas"] if a["key"] == "pdca")
    assert pdca["perms"]["control_owner"] == "W" and pdca["perms"]["internal_auditor"] == "R"
    users = next(a for a in data["areas"] if a["key"] == "users")
    assert users["perms"]["super_admin"] == "W" and users["perms"]["compliance_officer"] == "-"


def test_every_role_scoped_permission_is_in_the_matrix():
    """Guardia: una nuova permission class deve comparire nella matrice dei ruoli."""
    import glob
    import importlib
    import inspect
    import os

    from apps.auth_grc.services import ROLE_MATRIX_AREAS, ROLE_MATRIX_EXCLUDED
    from core.permissions import RoleScopedPermission

    mapped = {path for _, path in ROLE_MATRIX_AREAS} | ROLE_MATRIX_EXCLUDED
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    found = set()
    for f in glob.glob(os.path.join(base, "*", "permissions.py")):
        mod = importlib.import_module(f"apps.{os.path.basename(os.path.dirname(f))}.permissions")
        for name, cls in inspect.getmembers(mod, inspect.isclass):
            if issubclass(cls, RoleScopedPermission) and cls is not RoleScopedPermission \
                    and cls.__module__ == mod.__name__:
                found.add(f"{mod.__name__}.{name}")
    assert found - mapped == set()

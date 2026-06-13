"""Fase 2 — assegnazione accesso per-sito via UserPlantAccessViewSet."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.auth_grc.models import GrcRole, UserPlantAccess

User = get_user_model()

URL = "/api/v1/auth/plant-access/"


@pytest.fixture
def admin_client(db):
    u = User.objects.create_user(username="f2admin", email="f2@a.test", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.SUPER_ADMIN, scope_type="org")
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.fixture
def topo(db):
    from apps.plants.models import BusinessUnit, Plant
    bu = BusinessUnit.objects.create(code="F2BU", name="BU F2")
    pa = Plant.objects.create(code="F2A", name="Plant F2A", country="IT", bu=bu,
                              nis2_scope="importante", status="attivo")
    pb = Plant.objects.create(code="F2B", name="Plant F2B", country="IT", bu=bu,
                              nis2_scope="importante", status="attivo")
    target = User.objects.create_user(username="f2target", email="f2t@a.test", password="x")
    return pa, pb, target


@pytest.mark.django_db
def test_assign_plant_manager_to_subset_of_sites(admin_client, topo):
    """Il caso d'uso: plant manager su 2 siti su 3 (qui 1 su 2)."""
    from core.scoping import get_user_plant_ids
    pa, pb, target = topo
    resp = admin_client.post(URL, {
        "user": target.id, "role": GrcRole.PLANT_MANAGER,
        "scope_type": "single_plant", "scope_plants": [str(pa.id)],
    }, format="json")
    assert resp.status_code == 201, resp.data
    assert get_user_plant_ids(target) == {pa.id}  # accesso reale solo a pa


@pytest.mark.django_db
def test_non_org_scope_without_sites_rejected(admin_client, topo):
    """Mezzo-bug chiuso: un perimetro per-sito senza siti non crea accesso vuoto."""
    pa, pb, target = topo
    resp = admin_client.post(URL, {
        "user": target.id, "role": GrcRole.PLANT_MANAGER, "scope_type": "single_plant",
    }, format="json")
    assert resp.status_code == 400
    assert "scope_plants" in resp.data


@pytest.mark.django_db
def test_filter_by_user(admin_client, topo):
    pa, pb, target = topo
    acc = UserPlantAccess.objects.create(user=target, role=GrcRole.CONTROL_OWNER, scope_type="single_plant")
    acc.scope_plants.add(pa)
    resp = admin_client.get(f"{URL}?user={target.id}")
    assert resp.status_code == 200
    rows = resp.data["results"] if isinstance(resp.data, dict) else resp.data
    assert all(r["user"] == target.id for r in rows)
    assert any(r["scope_plant_codes"] == ["F2A"] for r in rows)


@pytest.mark.django_db
def test_assign_role_endpoint_rejects_non_org_scope(admin_client, topo):
    """assign_role è ora solo org: i perimetri per-sito passano dal plant-access."""
    pa, pb, target = topo
    resp = admin_client.post(f"/api/v1/auth/users/{target.id}/assign_role/",
                             {"role": GrcRole.PLANT_MANAGER, "scope_type": "single_plant"},
                             format="json")
    assert resp.status_code == 400

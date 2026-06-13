"""Test della review prod-readiness M01 (2026-06-13).

Copre: soft delete + audit della Business Unit (prima hard delete senza audit),
validazione del vincolo di nesting parent_plant (DRF non chiama Plant.clean()),
e read_only su created_by del Plant.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_BU = "/api/v1/plants/business-units/"
URL_PLANTS = "/api/v1/plants/plants/"


@pytest.fixture
def admin(db):
    u = User.objects.create_user(username="plant_admin", email="pa@test.com", password="test")
    u.is_superuser = True
    u.is_staff = True
    u.save()
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    UserPlantAccess.objects.create(user=u, role=GrcRole.SUPER_ADMIN, scope_type="org")
    return u


@pytest.fixture
def client(admin):
    c = APIClient()
    c.force_authenticate(user=admin)
    return c


@pytest.mark.django_db
def test_business_unit_delete_is_soft_and_audited(client):
    from apps.plants.models import BusinessUnit
    from core.audit import AuditLog

    bu = BusinessUnit.objects.create(code="BU-DEL", name="BU da eliminare")
    resp = client.delete(f"{URL_BU}{bu.id}/")
    assert resp.status_code == 204

    bu.refresh_from_db()
    assert bu.deleted_at is not None  # soft delete
    assert not BusinessUnit.objects.filter(pk=bu.id).exists()  # fuori dal manager default
    assert AuditLog.objects.filter(action_code="plants.business_unit.delete").exists()


@pytest.mark.django_db
def test_plant_nesting_constraint_enforced_via_api(client):
    """Plant.clean() non viene chiamato da DRF: il vincolo max-1-livello è ora
    replicato nel serializer."""
    from apps.plants.models import Plant

    root = Plant.objects.create(code="ROOT", name="Root", country="IT",
                                nis2_scope="importante", status="attivo")
    child = Plant.objects.create(code="CHILD", name="Child", country="IT",
                                 nis2_scope="importante", status="attivo", parent_plant=root)

    # Tentativo: creare un nipote sotto un sito che è già un sotto-sito → 400
    resp = client.post(URL_PLANTS, {
        "code": "GRANDCHILD", "name": "Grandchild", "country": "IT",
        "nis2_scope": "importante", "status": "attivo",
        "parent_plant": str(child.id),
    }, format="json")
    assert resp.status_code == 400
    assert "parent_plant" in resp.data


@pytest.mark.django_db
def test_plant_created_by_read_only(client, admin):
    from apps.plants.models import Plant

    other = User.objects.create_user(username="other_p", email="op@test.com", password="test")
    resp = client.post(URL_PLANTS, {
        "code": "RO1", "name": "RO Plant", "country": "IT",
        "nis2_scope": "importante", "status": "attivo",
        "created_by": str(other.id),  # spoofing → ignorato
    }, format="json")
    assert resp.status_code == 201
    p = Plant.objects.get(pk=resp.data["id"])
    # created_by non è impostato dal client; perform_create del viewset non lo
    # forza qui, ma il campo read_only impedisce lo spoofing → resta None.
    assert p.created_by_id != other.id

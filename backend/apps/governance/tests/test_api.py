"""Test API governance — ruoli, comitati."""
import pytest
from datetime import date
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_ROLES = "/api/v1/governance/role-assignments/"
URL_COMMITTEES = "/api/v1/governance/committees/"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="gov_api", email="govapi@test.com", password="test")


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="GVA-P", name="Plant GOV API", country="IT", nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def role_assignment(db, user):
    from apps.governance.models import RoleAssignment, NormativeRole
    return RoleAssignment.objects.create(
        user=user,
        role=NormativeRole.CISO,
        scope_type="org",
        valid_from=date.today(),
    )


# ── RoleAssignment CRUD ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_role_assignments(client):
    resp = client.get(URL_ROLES)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_list_role_assignments_unauthenticated():
    resp = APIClient().get(URL_ROLES)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_create_role_assignment(client, user):
    payload = {
        "user": str(user.id),
        "role": "compliance_officer",
        "scope_type": "org",
        "valid_from": str(date.today()),
    }
    resp = client.post(URL_ROLES, payload, format="json")
    assert resp.status_code == 201


@pytest.mark.django_db
def test_retrieve_role_assignment(client, role_assignment):
    resp = client.get(f"{URL_ROLES}{role_assignment.id}/")
    assert resp.status_code == 200
    assert resp.data["role"] == "ciso"


@pytest.mark.django_db
def test_vacanti_endpoint(client):
    resp = client.get(f"{URL_ROLES}vacanti/")
    assert resp.status_code == 200
    assert "vacant_roles" in resp.data


@pytest.mark.django_db
def test_in_scadenza_endpoint(client):
    resp = client.get(f"{URL_ROLES}in-scadenza/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_termina_role_assignment(client, role_assignment):
    payload = {"reason": "Cambio ruolo", "termination_date": str(date.today())}
    resp = client.post(f"{URL_ROLES}{role_assignment.id}/termina/", payload, format="json")
    assert resp.status_code in (200, 201)
    role_assignment.refresh_from_db()
    assert role_assignment.valid_until is not None


# ── Committees ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_committees(client):
    resp = client.get(URL_COMMITTEES)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_create_committee(client, plant):
    payload = {
        "plant": str(plant.id),
        "name": "Comitato Sicurezza",
        "committee_type": "bu",
        "frequency": "trimestrale",
    }
    resp = client.post(URL_COMMITTEES, payload, format="json")
    assert resp.status_code == 201

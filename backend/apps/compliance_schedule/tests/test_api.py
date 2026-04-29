"""Test API compliance schedule."""
import pytest
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_POLICIES = "/api/v1/schedule/policies/"
URL_REQ_DOCS = "/api/v1/schedule/required-documents/"


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="cs_user", email="cs@test.com", password="test")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="CS-P", name="Plant CS", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def policy(db, plant, user):
    from apps.compliance_schedule.models import ComplianceSchedulePolicy
    return ComplianceSchedulePolicy.objects.create(
        plant=plant,
        name="Policy ISO 27001",
        is_active=True,
        valid_from=date.today(),
        created_by=user,
    )


# ── Policies ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_policies_authenticated(client):
    resp = client.get(URL_POLICIES)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_list_policies_unauthenticated():
    resp = APIClient().get(URL_POLICIES)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_create_policy(client, plant):
    payload = {
        "plant": str(plant.id),
        "name": "NIS2 Policy",
        "is_active": True,
        "valid_from": str(date.today()),
    }
    resp = client.post(URL_POLICIES, payload, format="json")
    assert resp.status_code == 201
    assert resp.data["name"] == "NIS2 Policy"


@pytest.mark.django_db
def test_retrieve_policy(client, policy):
    resp = client.get(f"{URL_POLICIES}{policy.id}/")
    assert resp.status_code == 200
    assert resp.data["name"] == "Policy ISO 27001"


@pytest.mark.django_db
def test_update_policy(client, policy):
    resp = client.patch(f"{URL_POLICIES}{policy.id}/", {"name": "Updated Policy"}, format="json")
    assert resp.status_code == 200
    assert resp.data["name"] == "Updated Policy"


@pytest.mark.django_db
def test_delete_policy(client, policy):
    resp = client.delete(f"{URL_POLICIES}{policy.id}/")
    assert resp.status_code == 204


# ── Required documents ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_required_docs(client):
    resp = client.get(URL_REQ_DOCS)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_filter_policies_by_plant(client, plant, policy):
    resp = client.get(f"{URL_POLICIES}?plant={plant.id}")
    assert resp.status_code == 200

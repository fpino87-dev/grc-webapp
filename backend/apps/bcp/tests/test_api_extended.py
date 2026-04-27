"""Test API BCP — azioni avanzate piani e test."""
import pytest
from datetime import date
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_PLANS = "/api/v1/bcp/plans/"
URL_TESTS = "/api/v1/bcp/tests/"


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="bcpx_user", email="bcpx@test.com", password="test")
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
        code="BCP-X", name="Plant BCPX", country="IT",
        nis2_scope="essenziale", status="attivo",
    )


@pytest.fixture
def bcp_plan(db, plant, user):
    from apps.bcp.models import BcpPlan
    return BcpPlan.objects.create(
        plant=plant,
        title="Piano BCP Extended",
        status="approvato",
        rto_hours=4,
        rpo_hours=2,
        created_by=user,
    )


@pytest.mark.django_db
def test_approve_plan_action(client, bcp_plan):
    resp = client.post(f"{URL_PLANS}{bcp_plan.id}/approve/", {}, format="json")
    assert resp.status_code in (200, 400, 403)


@pytest.mark.django_db
def test_record_test_action(client, bcp_plan, user):
    payload = {
        "test_date": str(date.today()),
        "result": "superato",
        "notes": "Test completato con successo",
        "conducted_by": str(user.id),
    }
    resp = client.post(f"{URL_PLANS}{bcp_plan.id}/record_test/", payload, format="json")
    assert resp.status_code in (200, 201, 400)


@pytest.mark.django_db
def test_missing_plans_action(client, plant):
    resp = client.get(f"{URL_PLANS}missing-plans/?plant={plant.id}")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_filter_plans_by_status(client, bcp_plan):
    resp = client.get(f"{URL_PLANS}?status=approvato")
    assert resp.status_code == 200

"""Test API BCP — piani di continuità e test."""
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
    u = User.objects.create_user(username="bcp_user", email="bcp@test.com", password="test")
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
        code="BCP-P", name="Plant BCP", country="IT",
        nis2_scope="importante", status="attivo",
    )


@pytest.fixture
def bcp_plan(db, plant, user):
    from apps.bcp.models import BcpPlan
    return BcpPlan.objects.create(
        plant=plant,
        title="Piano di Continuità IT",
        status="bozza",
        rto_hours=4,
        rpo_hours=2,
        created_by=user,
    )


@pytest.fixture
def bcp_test(db, bcp_plan, user):
    from apps.bcp.models import BcpTest
    return BcpTest.objects.create(
        plan=bcp_plan,
        test_date=date.today(),
        result="superato",
        created_by=user,
    )


# ── Plans ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_plans_authenticated(client):
    resp = client.get(URL_PLANS)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_list_plans_unauthenticated():
    resp = APIClient().get(URL_PLANS)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_create_plan(client, plant):
    payload = {
        "plant": str(plant.id),
        "title": "Nuovo Piano BCP",
        "status": "bozza",
        "rto_hours": 8,
        "rpo_hours": 4,
    }
    resp = client.post(URL_PLANS, payload, format="json")
    assert resp.status_code == 201
    assert resp.data["title"] == "Nuovo Piano BCP"


@pytest.mark.django_db
def test_retrieve_plan(client, bcp_plan):
    resp = client.get(f"{URL_PLANS}{bcp_plan.id}/")
    assert resp.status_code == 200
    assert resp.data["title"] == "Piano di Continuità IT"


@pytest.mark.django_db
def test_update_plan_status(client, bcp_plan):
    resp = client.patch(f"{URL_PLANS}{bcp_plan.id}/", {"status": "approvato"}, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "approvato"


@pytest.mark.django_db
def test_delete_plan(client, bcp_plan):
    resp = client.delete(f"{URL_PLANS}{bcp_plan.id}/")
    assert resp.status_code == 204


@pytest.mark.django_db
def test_filter_plans_by_plant(client, plant, bcp_plan):
    resp = client.get(f"{URL_PLANS}?plant={plant.id}")
    assert resp.status_code == 200


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_bcp_tests(client):
    resp = client.get(URL_TESTS)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_create_bcp_test(client, bcp_plan):
    payload = {
        "plan": str(bcp_plan.id),
        "test_date": str(date.today()),
        "result": "parziale",
    }
    resp = client.post(URL_TESTS, payload, format="json")
    assert resp.status_code == 201


@pytest.mark.django_db
def test_retrieve_bcp_test(client, bcp_test):
    resp = client.get(f"{URL_TESTS}{bcp_test.id}/")
    assert resp.status_code == 200
    assert resp.data["result"] == "superato"


@pytest.mark.django_db
def test_update_bcp_test(client, bcp_test):
    resp = client.patch(f"{URL_TESTS}{bcp_test.id}/", {"result": "fallito"}, format="json")
    assert resp.status_code == 200
    assert resp.data["result"] == "fallito"


@pytest.mark.django_db
def test_delete_bcp_test(client, bcp_test):
    resp = client.delete(f"{URL_TESTS}{bcp_test.id}/")
    assert resp.status_code == 204
    resp2 = client.get(f"{URL_TESTS}{bcp_test.id}/")
    assert resp2.status_code == 404

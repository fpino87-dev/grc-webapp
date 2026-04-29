"""Test API compliance schedule — azioni avanzate."""
import pytest
from datetime import date
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_POLICIES = "/api/v1/schedule/policies/"
URL_REQ_DOCS = "/api/v1/schedule/required-documents/"
URL_ACTIVITY = "/api/v1/schedule/activity/"
URL_REQ_DOCS_STATUS = "/api/v1/schedule/required-documents-status/"
URL_RULE_TYPES = "/api/v1/schedule/rule-types/"


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="csx_user", email="csx@test.com", password="test")
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
        code="CS-X", name="Plant CSX", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def policy(db, plant, user):
    from apps.compliance_schedule.models import ComplianceSchedulePolicy
    return ComplianceSchedulePolicy.objects.create(
        plant=plant,
        name="Policy Test Extended",
        is_active=True,
        valid_from=date.today(),
        created_by=user,
    )


@pytest.mark.django_db
def test_activity_schedule_view(client):
    resp = client.get(URL_ACTIVITY)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_required_documents_status_view(client):
    resp = client.get(URL_REQ_DOCS_STATUS)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_rule_type_catalogue_view(client):
    resp = client.get(URL_RULE_TYPES)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_create_default_action(client, plant):
    payload = {"plant": str(plant.id)}
    resp = client.post(f"{URL_POLICIES}create-default/", payload, format="json")
    assert resp.status_code in (200, 201, 400)


@pytest.mark.django_db
def test_activity_schedule_with_plant_filter(client, plant):
    resp = client.get(f"{URL_ACTIVITY}?plant={plant.id}")
    assert resp.status_code == 200

"""Test API governance — azioni avanzate organigramma e ruoli."""
import pytest
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_ASSIGNMENTS = "/api/v1/governance/role-assignments/"
URL_COMMITTEES = "/api/v1/governance/committees/"
URL_DWP = "/api/v1/governance/document-workflow-policies/"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="gov_x", email="govx@test.com", password="test")


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def role_assignment(db, user):
    from apps.governance.models import RoleAssignment, NormativeRole
    return RoleAssignment.objects.create(
        user=user,
        role=NormativeRole.CISO,
        scope_type="org",
        valid_from=date.today(),
    )


@pytest.mark.django_db
def test_list_role_assignments(client):
    resp = client.get(URL_ASSIGNMENTS)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_create_role_assignment(client, user):
    from apps.governance.models import NormativeRole
    payload = {
        "user": str(user.id),
        "role": NormativeRole.DPO,
        "scope_type": "org",
        "valid_from": str(date.today()),
    }
    resp = client.post(URL_ASSIGNMENTS, payload, format="json")
    assert resp.status_code == 201


@pytest.mark.django_db
def test_retrieve_role_assignment(client, role_assignment):
    resp = client.get(f"{URL_ASSIGNMENTS}{role_assignment.id}/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_update_role_assignment(client, role_assignment):
    resp = client.patch(
        f"{URL_ASSIGNMENTS}{role_assignment.id}/",
        {"valid_until": str(date.today() + timedelta(days=90))},
        format="json",
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_delete_role_assignment(client, role_assignment):
    resp = client.delete(f"{URL_ASSIGNMENTS}{role_assignment.id}/")
    assert resp.status_code == 204


@pytest.mark.django_db
def test_termina_action(client, role_assignment):
    payload = {"termination_date": str(date.today() - timedelta(days=1)), "reason": "Dimissioni"}
    resp = client.post(f"{URL_ASSIGNMENTS}{role_assignment.id}/termina/", payload, format="json")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_vacanti_action(client):
    resp = client.get(f"{URL_ASSIGNMENTS}vacanti/")
    assert resp.status_code == 200
    assert "vacant_roles" in resp.data


@pytest.mark.django_db
def test_in_scadenza_action(client, role_assignment):
    resp = client.get(f"{URL_ASSIGNMENTS}in-scadenza/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_filter_assignments_by_user(client, user, role_assignment):
    resp = client.get(f"{URL_ASSIGNMENTS}?user={user.id}")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_list_committees(client):
    resp = client.get(URL_COMMITTEES)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_list_document_workflow_policies(client):
    resp = client.get(URL_DWP)
    assert resp.status_code == 200

"""Test API task management."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL = "/api/v1/tasks/tasks/"


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="task_user", email="task@test.com", password="test")
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
    return Plant.objects.create(code="TSK-P", name="Plant Tasks", country="IT", nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def task(db, plant, user):
    from apps.tasks.models import Task
    return Task.objects.create(
        plant=plant,
        title="Task di test",
        priority="media",
        status="aperto",
        assigned_to=user,
        created_by=user,
    )


# ── CRUD ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_tasks_authenticated(client):
    resp = client.get(URL)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_list_tasks_unauthenticated():
    resp = APIClient().get(URL)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_create_task(client, plant, user):
    payload = {
        "plant": str(plant.id),
        "title": "Nuovo task",
        "priority": "alta",
        "status": "aperto",
        "assigned_to": str(user.id),
    }
    resp = client.post(URL, payload, format="json")
    assert resp.status_code == 201
    assert resp.data["title"] == "Nuovo task"


@pytest.mark.django_db
def test_retrieve_task(client, task):
    resp = client.get(f"{URL}{task.id}/")
    assert resp.status_code == 200
    assert resp.data["title"] == "Task di test"


@pytest.mark.django_db
def test_update_task_priority(client, task):
    resp = client.patch(f"{URL}{task.id}/", {"priority": "critica"}, format="json")
    assert resp.status_code == 200
    assert resp.data["priority"] == "critica"


@pytest.mark.django_db
def test_delete_task_soft(client, task):
    resp = client.delete(f"{URL}{task.id}/")
    assert resp.status_code == 204
    task.refresh_from_db()
    assert task.deleted_at is not None


# ── Custom actions ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_complete_task_action(client, task):
    resp = client.post(f"{URL}{task.id}/complete/", {"notes": "Fatto!"}, format="json")
    assert resp.status_code == 200
    task.refresh_from_db()
    assert task.status == "completato"
    assert task.completed_at is not None


@pytest.mark.django_db
def test_escalate_task_action(client, task):
    resp = client.post(f"{URL}{task.id}/escalate/", {}, format="json")
    assert resp.status_code == 200
    task.refresh_from_db()
    assert task.escalation_level == 1


@pytest.mark.django_db
def test_overdue_tasks_endpoint(client, plant, user):
    from apps.tasks.models import Task
    from datetime import date, timedelta
    Task.objects.create(
        plant=plant,
        title="Scaduto",
        priority="alta",
        status="aperto",
        assigned_to=user,
        due_date=date.today() - timedelta(days=1),
        created_by=user,
    )
    resp = client.get(f"{URL}overdue/")
    assert resp.status_code == 200
    assert len(resp.data) >= 1


@pytest.mark.django_db
def test_complete_task_already_completed(client, task):
    task.status = "completato"
    task.save()
    resp = client.post(f"{URL}{task.id}/complete/", {}, format="json")
    # Should return 200 or 400 depending on service validation
    assert resp.status_code in (200, 400)

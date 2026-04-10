"""Test services task management."""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="svc_user", email="svc@test.com", password="test")


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="SVC-P", name="Plant SVC", country="IT", nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def open_task(db, plant, user):
    from apps.tasks.models import Task
    return Task.objects.create(
        plant=plant,
        title="Task aperto",
        priority="media",
        status="aperto",
        assigned_to=user,
        created_by=user,
    )


# ── create_task ───────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_task_service_basic(plant, user):
    from apps.tasks.services import create_task
    task = create_task(
        plant=plant,
        title="Task da service",
        priority="alta",
        source_module="M03",
    )
    assert task.id is not None
    assert task.title == "Task da service"
    assert task.source == "controllo"
    assert task.priority == "alta"


@pytest.mark.django_db
def test_create_task_with_user_assignment(plant, user):
    from apps.tasks.services import create_task
    task = create_task(
        plant=plant,
        title="Task assegnato",
        assign_type="user",
        assign_value=str(user.id),
    )
    assert task.assigned_to == user


@pytest.mark.django_db
def test_create_task_source_mapping(plant):
    from apps.tasks.services import create_task
    mappings = [
        ("M06", "rischio"),
        ("M09", "incidente"),
        ("M11", "pdca"),
        ("M17", "audit"),
        ("M99", "manuale"),
    ]
    for module, expected_source in mappings:
        task = create_task(plant=plant, title=f"Task {module}", source_module=module)
        assert task.source == expected_source, f"Module {module} → expected {expected_source}, got {task.source}"


# ── complete_task ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_complete_task_sets_status(open_task, user):
    from apps.tasks.services import complete_task
    complete_task(open_task, user, notes="Completato con successo")
    open_task.refresh_from_db()
    assert open_task.status == "completato"
    assert open_task.completed_by == user
    assert open_task.completed_at is not None


@pytest.mark.django_db
def test_complete_task_notes_saved(open_task, user):
    from apps.tasks.services import complete_task
    complete_task(open_task, user, notes="Note importanti")
    open_task.refresh_from_db()
    assert "Note importanti" in (open_task.notes or "")


# ── escalate_task ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_escalate_task_increments_level(open_task, user):
    from apps.tasks.services import escalate_task
    assert open_task.escalation_level == 0
    escalate_task(open_task, user)
    open_task.refresh_from_db()
    assert open_task.escalation_level == 1

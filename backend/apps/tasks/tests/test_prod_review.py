"""Review prod-readiness M08 (2026-06-13).

TaskCommentViewSet eliminava i commenti (thread di discussione) con HARD delete
senza audit. Ora soft delete + audit.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.auth_grc.models import GrcRole, UserPlantAccess

User = get_user_model()


@pytest.fixture
def admin_client(db):
    u = User.objects.create_user(username="m8admin", email="m8@a.test", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    c = APIClient()
    c.force_authenticate(user=u)
    return u, c


@pytest.fixture
def task(db):
    from apps.tasks.models import Task
    from apps.plants.models import Plant
    plant = Plant.objects.create(code="M8P", name="M8 Plant", country="IT",
                                 nis2_scope="importante", status="attivo")
    return Task.objects.create(plant=plant, title="T", priority="media", status="aperto")


@pytest.mark.django_db
def test_task_comment_delete_is_soft_and_audited(admin_client, task):
    from apps.tasks.models import TaskComment
    from core.audit import AuditLog
    user, client = admin_client
    cm = TaskComment.objects.create(task=task, author=user, body="hello")
    resp = client.delete(f"/api/v1/tasks/task-comments/{cm.id}/")
    assert resp.status_code == 204
    cm.refresh_from_db()
    assert cm.deleted_at is not None
    assert not TaskComment.objects.filter(pk=cm.id).exists()
    assert AuditLog.objects.filter(action_code="tasks.task_comment.delete").exists()

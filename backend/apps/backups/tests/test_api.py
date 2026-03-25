"""
Test API Backup: permessi, list, create, delete.
"""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def super_admin(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    user = User.objects.create_superuser(username="sa@bk.com", email="sa@bk.com", password="x")
    UserPlantAccess.objects.create(user=user, role=GrcRole.SUPER_ADMIN, scope_type="org")
    return user


@pytest.fixture
def co_user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    user = User.objects.create_user(username="co@bk.com", email="co@bk.com", password="x")
    UserPlantAccess.objects.create(user=user, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return user


@pytest.fixture
def sa_client(super_admin):
    c = APIClient()
    c.force_authenticate(user=super_admin)
    return c


@pytest.fixture
def co_client(co_user):
    c = APIClient()
    c.force_authenticate(user=co_user)
    return c


@pytest.fixture
def completed_backup(db, super_admin):
    from apps.backups.models import BackupRecord
    return BackupRecord.objects.create(
        filename="backup_20260101_020000_auto.dump",
        status=BackupRecord.Status.COMPLETED,
        size_bytes=512000,
        backup_type=BackupRecord.BackupType.AUTO,
        created_by=super_admin,
    )


# ── Permessi ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_backups_unauthenticated():
    res = APIClient().get("/api/v1/backups/")
    assert res.status_code == 401


@pytest.mark.django_db
def test_list_backups_compliance_officer_forbidden(co_client):
    res = co_client.get("/api/v1/backups/")
    assert res.status_code == 403


@pytest.mark.django_db
def test_list_backups_super_admin_ok(sa_client):
    res = sa_client.get("/api/v1/backups/")
    assert res.status_code == 200


# ── List ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_returns_backup_records(sa_client, completed_backup):
    res = sa_client.get("/api/v1/backups/")
    assert res.status_code == 200
    ids = [b["id"] for b in (res.data.get("results") or res.data)]
    assert str(completed_backup.pk) in ids


# ── Create ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_backup_endpoint_returns_201(sa_client, tmp_path):
    def fake_run(cmd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        Path(cmd[-1]).write_bytes(b"dump")
        return r

    with patch("apps.backups.services.BACKUP_DIR", tmp_path), \
         patch("apps.backups.services.subprocess.run", side_effect=fake_run):
        res = sa_client.post("/api/v1/backups/create/")

    assert res.status_code == 201
    assert res.data["status"] == "completed"


@pytest.mark.django_db
def test_create_backup_forbidden_for_co(co_client):
    res = co_client.post("/api/v1/backups/create/")
    assert res.status_code == 403


# ── Delete ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_delete_backup_soft_deletes(sa_client, completed_backup, tmp_path):
    with patch("apps.backups.services.BACKUP_DIR", tmp_path):
        res = sa_client.delete(f"/api/v1/backups/{completed_backup.pk}/remove/")
    assert res.status_code == 204

    # Non più visibile
    res2 = sa_client.get(f"/api/v1/backups/{completed_backup.pk}/")
    assert res2.status_code == 404

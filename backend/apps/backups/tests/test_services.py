"""
Test services backup: create_backup (mock subprocess), cleanup_old_backups.
"""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="admin@test.com", email="admin@test.com", password="x"
    )


@pytest.fixture(autouse=True)
def patch_backup_dir(tmp_path, monkeypatch):
    """Usa una directory temporanea per i backup durante i test."""
    monkeypatch.setattr("apps.backups.services.BACKUP_DIR", tmp_path)
    return tmp_path


# ── create_backup ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_backup_success(admin_user, tmp_path):
    from apps.backups.services import create_backup

    def fake_run(cmd, env, capture_output, text, timeout):
        r = MagicMock()
        r.returncode = 0
        # Crea il file dump finto
        filepath = Path(cmd[-1])
        filepath.write_bytes(b"FAKE_DUMP_DATA")
        return r

    with patch("apps.backups.services.subprocess.run", side_effect=fake_run):
        record = create_backup(admin_user, backup_type="manual")

    assert record.status == "completed"
    assert record.size_bytes == len(b"FAKE_DUMP_DATA")
    assert record.filename.startswith("backup_")
    assert record.filename.endswith("_manual.dump")
    assert record.completed_at is not None


@pytest.mark.django_db
def test_create_backup_pg_dump_failure(admin_user):
    from apps.backups.services import create_backup
    from core.audit import AuditLog

    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "pg_dump: error: connection to server failed"

    with patch("apps.backups.services.subprocess.run", return_value=mock_result):
        record = create_backup(admin_user, backup_type="manual")

    assert record.status == "failed"
    assert "connection to server" in record.error_message
    # newfix F2 — il fallimento deve produrre un audit BACKUP_FAILED.
    audit = AuditLog.objects.filter(
        action_code="BACKUP_FAILED", entity_id=record.pk,
    ).first()
    assert audit is not None
    assert audit.payload.get("stage") == "pg_dump"


@pytest.mark.django_db
def test_create_backup_timeout(admin_user):
    import subprocess
    from apps.backups.services import create_backup
    from core.audit import AuditLog

    with patch("apps.backups.services.subprocess.run", side_effect=subprocess.TimeoutExpired("pg_dump", 300)):
        record = create_backup(admin_user)

    assert record.status == "failed"
    assert "Timeout" in record.error_message
    # newfix F2 — anche il timeout produce un audit con stage='pg_dump'.
    assert AuditLog.objects.filter(
        action_code="BACKUP_FAILED", entity_id=record.pk,
    ).exists()


@pytest.mark.django_db
def test_create_backup_type_auto(admin_user, tmp_path):
    from apps.backups.services import create_backup

    def fake_run(cmd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        Path(cmd[-1]).write_bytes(b"x")
        return r

    with patch("apps.backups.services.subprocess.run", side_effect=fake_run):
        record = create_backup(admin_user, backup_type="auto")

    assert record.backup_type == "auto"
    assert "_auto.dump" in record.filename


# ── cleanup_old_backups ───────────────────────────────────────────────────────

@pytest.mark.django_db
def test_cleanup_removes_old_completed_backups(admin_user, tmp_path):
    from apps.backups.models import BackupRecord
    from apps.backups.services import cleanup_old_backups

    # Backup vecchio (31 giorni fa)
    old_file = tmp_path / "backup_old.dump"
    old_file.write_bytes(b"old")
    old = BackupRecord.objects.create(
        filename="backup_old.dump",
        status=BackupRecord.Status.COMPLETED,
        size_bytes=3,
        created_by=admin_user,
    )
    BackupRecord.objects.filter(pk=old.pk).update(
        created_at=timezone.now() - timezone.timedelta(days=31)
    )

    count = cleanup_old_backups()

    assert count == 1
    assert not old_file.exists()
    assert BackupRecord.objects.filter(pk=old.pk).count() == 0  # soft deleted


@pytest.mark.django_db
def test_cleanup_keeps_recent_backups(admin_user, tmp_path):
    from apps.backups.models import BackupRecord
    from apps.backups.services import cleanup_old_backups

    recent_file = tmp_path / "backup_recent.dump"
    recent_file.write_bytes(b"recent")
    BackupRecord.objects.create(
        filename="backup_recent.dump",
        status=BackupRecord.Status.COMPLETED,
        size_bytes=6,
        created_by=admin_user,
    )

    count = cleanup_old_backups()

    assert count == 0
    assert recent_file.exists()


@pytest.mark.django_db
def test_cleanup_ignores_failed_backups(admin_user):
    from apps.backups.models import BackupRecord
    from apps.backups.services import cleanup_old_backups

    failed = BackupRecord.objects.create(
        filename="backup_failed.dump",
        status=BackupRecord.Status.FAILED,
        created_by=admin_user,
    )
    BackupRecord.objects.filter(pk=failed.pk).update(
        created_at=timezone.now() - timezone.timedelta(days=40)
    )

    count = cleanup_old_backups()
    assert count == 0  # i backup falliti non vengono toccati

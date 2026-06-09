"""
Test import backup (newfix F1): POST /api/v1/backups/import/.

Un file importato deve essere garantito ripristinabile al momento dell'accept:
magic PGDMP verificato sul plaintext e, per i .dump.enc, probe di decifratura
completa con la BACKUP_ENCRYPTION_KEY corrente.
"""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient

User = get_user_model()

PGDMP = b"PGDMP" + b"\x00fake-custom-format-body" * 10


@pytest.fixture
def super_admin(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    user = User.objects.create_superuser(username="sa@imp.com", email="sa@imp.com", password="x")
    UserPlantAccess.objects.create(user=user, role=GrcRole.SUPER_ADMIN, scope_type="org")
    return user


@pytest.fixture
def co_user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    user = User.objects.create_user(username="co@imp.com", email="co@imp.com", password="x")
    UserPlantAccess.objects.create(user=user, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return user


@pytest.fixture
def sa_client(super_admin):
    c = APIClient()
    c.force_authenticate(user=super_admin)
    return c


@pytest.fixture(autouse=True)
def patch_backup_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("apps.backups.services.BACKUP_DIR", tmp_path)
    return tmp_path


def _upload(name: str, content: bytes):
    return SimpleUploadedFile(name, content, content_type="application/octet-stream")


# ── Permessi / input ──────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_import_forbidden_for_co(co_user):
    c = APIClient()
    c.force_authenticate(user=co_user)
    res = c.post("/api/v1/backups/import/", {"file": _upload("x.dump", PGDMP)}, format="multipart")
    assert res.status_code == 403


@pytest.mark.django_db
def test_import_requires_file(sa_client):
    res = sa_client.post("/api/v1/backups/import/", {}, format="multipart")
    assert res.status_code == 400


# ── File in chiaro ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_import_valid_dump_creates_record(sa_client, patch_backup_dir):
    from apps.backups.models import BackupRecord
    from core.audit import AuditLog

    res = sa_client.post(
        "/api/v1/backups/import/",
        {"file": _upload("vecchio_backup.dump", PGDMP)},
        format="multipart",
    )
    assert res.status_code == 201
    assert res.data["backup_type"] == "imported"
    assert res.data["status"] == "completed"

    record = BackupRecord.objects.get(pk=res.data["id"])
    assert record.filename.endswith("_imported.dump")
    assert "vecchio_backup.dump" in record.notes
    assert (patch_backup_dir / record.filename).read_bytes() == PGDMP
    assert AuditLog.objects.filter(
        action_code="BACKUP_IMPORTED", entity_id=record.pk,
    ).exists()


@pytest.mark.django_db
def test_import_rejects_bad_magic(sa_client, patch_backup_dir):
    res = sa_client.post(
        "/api/v1/backups/import/",
        {"file": _upload("finto.dump", b"NOT-A-PG-DUMP")},
        format="multipart",
    )
    assert res.status_code == 400
    # Il file rifiutato non deve restare nella directory dei backup
    assert list(patch_backup_dir.iterdir()) == []


@pytest.mark.django_db
def test_import_rejects_bad_extension(sa_client):
    res = sa_client.post(
        "/api/v1/backups/import/",
        {"file": _upload("backup.sql", PGDMP)},
        format="multipart",
    )
    assert res.status_code == 400


@pytest.mark.django_db
def test_import_rejects_oversize(sa_client):
    with override_settings(BACKUP_IMPORT_MAX_BYTES=10):
        res = sa_client.post(
            "/api/v1/backups/import/",
            {"file": _upload("big.dump", PGDMP)},
            format="multipart",
        )
    assert res.status_code == 400
    assert "grande" in res.data["detail"]


# ── File cifrati ──────────────────────────────────────────────────────────────

def _encrypt_pgdmp(tmp_path: Path, passphrase: str) -> bytes:
    """Produce i bytes di un PGDMP cifrato con la passphrase data."""
    from apps.backups import encryption

    plain = tmp_path / "plain.dump"
    enc = tmp_path / "plain.dump.enc"
    plain.write_bytes(PGDMP)
    with override_settings(BACKUP_ENCRYPTION_KEY=passphrase):
        encryption.encrypt_file(plain, enc)
    data = enc.read_bytes()
    enc.unlink()
    return data


@pytest.mark.django_db
def test_import_enc_without_key_rejected(sa_client, tmp_path):
    data = _encrypt_pgdmp(tmp_path, "passphrase-di-test-123")
    with override_settings(BACKUP_ENCRYPTION_KEY=""):
        res = sa_client.post(
            "/api/v1/backups/import/",
            {"file": _upload("old.dump.enc", data)},
            format="multipart",
        )
    assert res.status_code == 400
    assert "BACKUP_ENCRYPTION_KEY" in res.data["detail"]


@pytest.mark.django_db
def test_import_enc_with_matching_key(sa_client, tmp_path, patch_backup_dir):
    from apps.backups.models import BackupRecord

    data = _encrypt_pgdmp(tmp_path, "passphrase-di-test-123")
    with override_settings(BACKUP_ENCRYPTION_KEY="passphrase-di-test-123"):
        res = sa_client.post(
            "/api/v1/backups/import/",
            {"file": _upload("old.dump.enc", data)},
            format="multipart",
        )
    assert res.status_code == 201
    record = BackupRecord.objects.get(pk=res.data["id"])
    assert record.encrypted is True
    assert record.filename.endswith("_imported.dump.enc")
    # Nessun file .probe residuo dopo la verifica
    assert all(not f.name.endswith(".probe") for f in patch_backup_dir.iterdir())


@pytest.mark.django_db
def test_import_enc_with_wrong_key_rejected(sa_client, tmp_path, patch_backup_dir):
    data = _encrypt_pgdmp(tmp_path, "passphrase-giusta-456")
    with override_settings(BACKUP_ENCRYPTION_KEY="passphrase-sbagliata-789"):
        res = sa_client.post(
            "/api/v1/backups/import/",
            {"file": _upload("old.dump.enc", data)},
            format="multipart",
        )
    assert res.status_code == 400
    assert "decifrabile" in res.data["detail"]
    assert list(patch_backup_dir.iterdir()) == []


# ── Round-trip: un import valido è ripristinabile ─────────────────────────────

@pytest.mark.django_db
def test_imported_backup_can_be_restored(sa_client, patch_backup_dir):
    res = sa_client.post(
        "/api/v1/backups/import/",
        {"file": _upload("vecchio.dump", PGDMP)},
        format="multipart",
    )
    assert res.status_code == 201

    def fake_run(cmd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        r.stderr = ""
        return r

    with patch("apps.backups.services.subprocess.run", side_effect=fake_run):
        res2 = sa_client.post(f"/api/v1/backups/{res.data['id']}/restore/")

    assert res2.status_code == 202
    from apps.backups.models import BackupRecord
    assert BackupRecord.objects.get(pk=res.data["id"]).status == "restored"

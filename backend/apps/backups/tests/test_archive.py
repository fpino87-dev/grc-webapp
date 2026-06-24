"""
Test del backup completo (DB + media): impacchettamento tar, estrazione del
dump, swap atomico del MEDIA_ROOT in restore, import di un archivio .tar.
"""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.backups import archive

User = get_user_model()

PGDMP = b"PGDMP" + b"\x00fake-custom-format-body" * 10


@pytest.fixture
def super_admin(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    user = User.objects.create_superuser(username="sa@arc.com", email="sa@arc.com", password="x")
    UserPlantAccess.objects.create(user=user, role=GrcRole.SUPER_ADMIN, scope_type="org")
    return user


@pytest.fixture
def sa_client(super_admin):
    c = APIClient()
    c.force_authenticate(user=super_admin)
    return c


def _make_archive(tmp_path, media_files: dict[str, bytes]) -> Path:
    """Crea un archivio tar (database.dump + media/...) con i file dati."""
    dump = tmp_path / "db.dump"
    dump.write_bytes(PGDMP)
    media_src = tmp_path / "media_src"
    media_src.mkdir()
    for rel, content in media_files.items():
        p = media_src / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
    arc = tmp_path / "backup.tar"
    with patch.object(archive, "_media_root", return_value=media_src):
        archive.build_archive(dump, arc)
    return arc


# ── helper archive ────────────────────────────────────────────────────────────

def test_is_full_archive_distinguishes_tar_from_raw_dump(tmp_path):
    arc = _make_archive(tmp_path, {"evidences/x.pdf": b"PDFDATA"})
    raw = tmp_path / "raw.dump"
    raw.write_bytes(PGDMP)
    assert archive.is_full_archive(arc) is True
    assert archive.is_full_archive(raw) is False


def test_read_db_dump_head_and_extract(tmp_path):
    arc = _make_archive(tmp_path, {"documents/d/v1/a.txt": b"hello"})
    assert archive.read_db_dump_head(arc) == archive.PGDMP_MAGIC
    out = tmp_path / "out.dump"
    archive.extract_db_dump(arc, out)
    assert out.read_bytes() == PGDMP


def test_restore_media_swaps_tree_atomically(tmp_path, settings):
    arc = _make_archive(tmp_path, {
        "plant-logos/p/logo.png": b"NEWLOGO",
        "evidences/e/file.pdf": b"NEWEV",
    })
    live = tmp_path / "media_live"
    live.mkdir()
    (live / "stale.txt").write_bytes(b"OLD")
    settings.MEDIA_ROOT = str(live)

    replaced = archive.restore_media(arc)

    assert replaced is True
    assert (live / "plant-logos/p/logo.png").read_bytes() == b"NEWLOGO"
    assert (live / "evidences/e/file.pdf").read_bytes() == b"NEWEV"
    # Il vecchio contenuto è stato sostituito, non fuso.
    assert not (live / "stale.txt").exists()
    # Nessuna staging/old residua nel parent.
    assert not any(p.name.startswith(".media_") for p in tmp_path.iterdir())


def test_restore_media_noop_when_archive_has_no_media(tmp_path, settings):
    dump = tmp_path / "db.dump"
    dump.write_bytes(PGDMP)
    empty_media = tmp_path / "empty"  # non esiste → archivio senza membri media
    arc = tmp_path / "nomedia.tar"
    with patch.object(archive, "_media_root", return_value=empty_media):
        archive.build_archive(dump, arc)

    live = tmp_path / "media_live"
    live.mkdir()
    (live / "keep.txt").write_bytes(b"KEEP")
    settings.MEDIA_ROOT = str(live)

    assert archive.restore_media(arc) is False
    assert (live / "keep.txt").read_bytes() == b"KEEP"


# ── import API di un archivio completo ────────────────────────────────────────

@pytest.fixture(autouse=True)
def patch_backup_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("apps.backups.services.BACKUP_DIR", tmp_path / "backups")
    (tmp_path / "backups").mkdir()


@pytest.mark.django_db
def test_import_full_tar_archive(sa_client, tmp_path):
    from apps.backups.models import BackupRecord

    arc = _make_archive(tmp_path, {"evidences/e/f.bin": b"DATA"})
    upload = SimpleUploadedFile(
        "full_backup.tar", arc.read_bytes(), content_type="application/octet-stream"
    )
    res = sa_client.post("/api/v1/backups/import/", {"file": upload}, format="multipart")

    assert res.status_code == 201, res.data
    record = BackupRecord.objects.get(pk=res.data["id"])
    assert record.filename.endswith("_imported.tar")
    assert record.status == "completed"


@pytest.mark.django_db
def test_restore_full_archive_restores_db_and_media(sa_client, tmp_path, settings, super_admin):
    """create_backup → restore: il media live viene sostituito con quello dell'archivio."""
    from apps.backups.services import create_backup, restore_backup

    # MEDIA_ROOT con contenuto "originale" al momento del backup.
    live = tmp_path / "media_live"
    live.mkdir()
    (live / "evidences").mkdir()
    (live / "evidences/orig.txt").write_bytes(b"ORIGINAL")
    settings.MEDIA_ROOT = str(live)

    def fake_dump(cmd, **kwargs):
        r = MagicMock(); r.returncode = 0
        Path(cmd[-1]).write_bytes(PGDMP)  # scrive il dump temporaneo
        return r

    with patch("apps.backups.services.subprocess.run", side_effect=fake_dump):
        record = create_backup(super_admin, backup_type="manual")
    assert record.status == "completed"
    assert record.filename.endswith(".tar")

    # Dopo il backup l'utente cancella un file media: il restore deve ripristinarlo.
    (live / "evidences/orig.txt").unlink()

    def fake_restore(cmd, **kwargs):
        r = MagicMock(); r.returncode = 0; r.stderr = ""
        return r

    with patch("apps.backups.services.subprocess.run", side_effect=fake_restore):
        restore_backup(record.pk, super_admin)

    record.refresh_from_db()
    assert record.status == "restored"
    assert (live / "evidences/orig.txt").read_bytes() == b"ORIGINAL"

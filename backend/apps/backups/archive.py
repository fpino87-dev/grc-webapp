"""
Archivio di backup completo: pg_dump del database + albero ``MEDIA_ROOT``
(documenti, evidenze, loghi plant) in un unico file tar.

Formato (membri del tar):
    database.dump   → pg_dump custom format (-Fc)
    media/...       → copia integrale di settings.MEDIA_ROOT

Un backup creato prima di questa feature è un singolo file pg_dump "grezzo"
(non un tar): :func:`is_full_archive` distingue i due casi così che il restore
resti retro-compatibile con i vecchi `.dump` (solo DB, nessun media).

Lo swap del media in restore è atomico (``os.rename`` sullo stesso filesystem):
MEDIA_ROOT non resta mai in uno stato parzialmente scritto.

La cifratura at-rest (encryption.py) usa streaming AES-GCM e file temporanei
privati, pubblicati solo dopo la verifica del tag di autenticazione.
"""
from __future__ import annotations

import logging
import os
import shutil
import tarfile
import uuid
from pathlib import Path, PurePosixPath

from django.conf import settings

logger = logging.getLogger("apps.backups")

DB_MEMBER = "database.dump"
MEDIA_PREFIX = "media"
PGDMP_MAGIC = b"PGDMP"


def _media_root() -> Path:
    return Path(settings.MEDIA_ROOT)


def build_archive(dump_path: Path, archive_path: Path) -> None:
    """Crea il tar con il dump DB (``database.dump``) e l'albero ``media/``.

    Se MEDIA_ROOT non esiste ancora (nessun upload), l'archivio contiene il
    solo dump: il restore di un archivio simile lascerà il media invariato.
    """
    media_root = _media_root()
    with open(archive_path, "xb", opener=lambda path, flags: os.open(path, flags, 0o600)) as output, \
            tarfile.open(fileobj=output, mode="w") as tar:
        tar.add(dump_path, arcname=DB_MEMBER)
        if media_root.exists():
            tar.add(media_root, arcname=MEDIA_PREFIX)


def is_full_archive(path: Path) -> bool:
    """True se ``path`` è un archivio tar (backup completo DB+media); False se
    è un dump pg_dump grezzo (formato legacy DB-only)."""
    try:
        return tarfile.is_tarfile(path)
    except (FileNotFoundError, OSError):
        return False


def _chown_tree(root: Path, uid: int, gid: int) -> None:
    """Chown ricorsivo di ``root`` (inclusa la radice) a ``uid:gid``.

    No-op sulle piattaforme prive di ``os.chown`` (Windows). I singoli errori
    (es. file già di proprietà nostra, EPERM da non-root) sono best-effort e non
    devono far fallire il restore."""
    if not hasattr(os, "chown"):
        return
    try:
        os.chown(root, uid, gid)
    except OSError:
        pass
    for dirpath, dirnames, filenames in os.walk(root):
        for name in dirnames + filenames:
            try:
                os.chown(os.path.join(dirpath, name), uid, gid, follow_symlinks=False)
            except OSError:
                pass


def _iter_safe_members(tar: tarfile.TarFile):
    """Restituisce i soli membri attesi (``database.dump`` o ``media/...``),
    sollevando ValueError su path assoluti, traversal o membri inattesi."""
    seen = set()
    total = 0
    max_bytes = getattr(settings, "BACKUP_ARCHIVE_MAX_BYTES", 20 * 1024**3)
    for m in tar:
        name = m.name
        parts = PurePosixPath(name).parts
        if (
            not parts or name.startswith("/") or ".." in parts or "\\" in name
            or (name != DB_MEMBER and parts[0] != MEDIA_PREFIX)
            or not (m.isfile() or m.isdir())
            or (name == DB_MEMBER and not m.isfile())
            or name in seen
        ):
            raise ValueError("Unsafe or duplicate backup archive member.")
        seen.add(name)
        total += m.size
        if len(seen) > 100000 or total > max_bytes:
            raise ValueError("Backup archive exceeds extraction limits.")
        yield m


def validate_archive(path: Path) -> None:
    """Validate ALL members before any database restore or media extraction."""
    with tarfile.open(path, "r") as tar:
        members = list(_iter_safe_members(tar))
        if not any(m.name == DB_MEMBER for m in members):
            raise ValueError("Archive has no database.dump.")


def read_db_dump_head(path: Path, n: int = len(PGDMP_MAGIC)) -> bytes:
    """Legge i primi ``n`` byte del membro ``database.dump`` nel tar (per la
    verifica del magic PGDMP in fase di import)."""
    validate_archive(path)
    with tarfile.open(path, "r") as tar:
        try:
            member = tar.getmember(DB_MEMBER)
        except KeyError:
            raise ValueError("Archivio privo del dump database (database.dump).") from None
        extracted = tar.extractfile(member)
        if extracted is None:
            raise ValueError("database.dump non leggibile nell'archivio.")
        with extracted:
            return extracted.read(n)


def extract_db_dump(path: Path, dest_dump: Path) -> None:
    """Estrae il solo ``database.dump`` dall'archivio in ``dest_dump``."""
    validate_archive(path)
    with tarfile.open(path, "r") as tar:
        try:
            member = tar.getmember(DB_MEMBER)
        except KeyError:
            raise ValueError("Archivio privo del dump database (database.dump).") from None
        src = tar.extractfile(member)
        if src is None:
            raise ValueError("database.dump non leggibile nell'archivio.")
        with src, open(dest_dump, "wb", opener=lambda path, flags: os.open(path, flags, 0o600)) as out:
            shutil.copyfileobj(src, out)


def restore_media(path: Path) -> bool:
    """Sostituisce l'intero MEDIA_ROOT con l'albero ``media/`` dell'archivio.

    Estrae prima in una staging directory sullo stesso filesystem di
    MEDIA_ROOT, poi fa swap atomico via ``os.rename``. Se l'archivio non
    contiene alcun membro ``media/`` il media corrente resta invariato.

    Restituisce True se il media è stato sostituito, False se non c'era nulla
    da ripristinare.
    """
    media_root = _media_root()
    parent = media_root.parent
    operation = uuid.uuid4().hex
    staging = parent / f".media_restore_{operation}"
    old_dir = parent / f".media_old_{operation}"

    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=True)

    try:
        with tarfile.open(path, "r") as tar:
            media_members = [
                m for m in _iter_safe_members(tar) if m.name != DB_MEMBER
            ]
            if not media_members:
                return False
            tar.extractall(path=staging, members=media_members, filter="data")

        extracted_media = staging / MEDIA_PREFIX
        if not extracted_media.exists():
            # Solo il dir entry "media" senza contenuto: tratta come media vuoto.
            extracted_media.mkdir(parents=True, exist_ok=True)

        # Riallinea l'ownership all'utente runtime del processo. Il tar preserva
        # uid/gid di chi ha creato il backup (potenzialmente un altro deploy): se
        # il restore gira da root quell'owner estraneo sopravvive e il container
        # applicativo — che gira come utente non privilegiato — non può più
        # scrivere in MEDIA_ROOT (upload → PermissionError → 500). Chown all'uid
        # corrente è idempotente: da non-root i file sono già di proprietà nostra.
        _chown_tree(extracted_media, os.getuid(), os.getgid())

        # Swap atomico. Se qualcosa fallisce dopo aver spostato via il vecchio
        # media, si tenta il rollback per non lasciare MEDIA_ROOT mancante.
        if old_dir.exists():
            shutil.rmtree(old_dir, ignore_errors=True)
        moved_old = False
        try:
            if media_root.exists():
                os.rename(media_root, old_dir)
                moved_old = True
            os.rename(extracted_media, media_root)
        except OSError:
            if moved_old and not media_root.exists():
                os.rename(old_dir, media_root)
            raise
        return True
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        # If both installation and rollback failed, old_dir is the only
        # remaining copy. Never delete it from the failure cleanup path.
        if media_root.exists():
            shutil.rmtree(old_dir, ignore_errors=True)

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

Nota: la cifratura at-rest (encryption.py) è single-shot e carica l'intero
archivio in memoria. Con i media inclusi l'archivio può crescere: per dataset
nell'ordine dei GB valutare uno streaming cipher (vedi commento in encryption.py).
"""
from __future__ import annotations

import logging
import os
import shutil
import tarfile
from pathlib import Path

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
    with tarfile.open(archive_path, "w") as tar:
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


def _iter_safe_members(tar: tarfile.TarFile):
    """Restituisce i soli membri attesi (``database.dump`` o ``media/...``),
    sollevando ValueError su path assoluti o traversal. Membri inattesi
    vengono ignorati."""
    for m in tar.getmembers():
        name = m.name
        if name != DB_MEMBER and name != MEDIA_PREFIX and not name.startswith(MEDIA_PREFIX + "/"):
            continue
        norm = os.path.normpath(name)
        if os.path.isabs(norm) or norm.startswith(".."):
            raise ValueError(f"Membro non sicuro nell'archivio: {name!r}")
        yield m


def read_db_dump_head(path: Path, n: int = len(PGDMP_MAGIC)) -> bytes:
    """Legge i primi ``n`` byte del membro ``database.dump`` nel tar (per la
    verifica del magic PGDMP in fase di import)."""
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
    with tarfile.open(path, "r") as tar:
        try:
            member = tar.getmember(DB_MEMBER)
        except KeyError:
            raise ValueError("Archivio privo del dump database (database.dump).") from None
        src = tar.extractfile(member)
        if src is None:
            raise ValueError("database.dump non leggibile nell'archivio.")
        with src, open(dest_dump, "wb") as out:
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
    staging = parent / f".media_restore_{os.getpid()}"
    old_dir = parent / f".media_old_{os.getpid()}"

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
            tar.extractall(path=staging, members=media_members)

        extracted_media = staging / MEDIA_PREFIX
        if not extracted_media.exists():
            # Solo il dir entry "media" senza contenuto: tratta come media vuoto.
            extracted_media.mkdir(parents=True, exist_ok=True)

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
        shutil.rmtree(old_dir, ignore_errors=True)

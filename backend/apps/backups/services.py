import logging
import os
import subprocess
from pathlib import Path

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("apps.backups")

BACKUP_DIR = Path(getattr(settings, "BACKUP_DIR", "/app/backups"))
BACKUP_RETENTION_DAYS = 30


def _ensure_backup_dir():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def _db_params() -> dict:
    db = settings.DATABASES["default"]
    return {
        "host":     db.get("HOST", "localhost"),
        "port":     str(db.get("PORT") or "5432"),
        "name":     db["NAME"],
        "user":     db.get("USER", ""),
        "password": db.get("PASSWORD", ""),
    }


def create_backup(user, backup_type: str = "manual"):
    from apps.backups.models import BackupRecord
    from core.audit import log_action

    _ensure_backup_dir()

    ts = timezone.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{ts}_{backup_type}.dump"
    filepath = BACKUP_DIR / filename

    record = BackupRecord.objects.create(
        filename=filename,
        status=BackupRecord.Status.RUNNING,
        backup_type=backup_type,
        created_by=user,
    )

    db = _db_params()
    env = os.environ.copy()
    env["PGPASSWORD"] = db["password"]

    cmd = [
        "pg_dump",
        "-Fc",            # custom format compresso
        "-h", db["host"],
        "-p", db["port"],
        "-U", db["user"],
        "-d", db["name"],
        "-f", str(filepath),
    ]

    try:
        result = subprocess.run(
            cmd, env=env, capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0:
            record.status        = BackupRecord.Status.FAILED
            record.error_message = result.stderr[:2000]
            record.completed_at  = timezone.now()
            record.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
            logger.error("Backup fallito: %s", result.stderr[:500])
        else:
            size = filepath.stat().st_size if filepath.exists() else 0
            record.status       = BackupRecord.Status.COMPLETED
            record.size_bytes   = size
            record.completed_at = timezone.now()
            record.save(update_fields=["status", "size_bytes", "completed_at", "updated_at"])
            log_action(
                user=user,
                action_code="BACKUP_CREATED",
                level="L2",
                entity=record,
                payload={"filename": filename, "size_bytes": size, "type": backup_type},
            )
            logger.info("Backup completato: %s (%d bytes)", filename, size)
    except subprocess.TimeoutExpired:
        record.status        = BackupRecord.Status.FAILED
        record.error_message = "Timeout: pg_dump ha impiegato più di 5 minuti."
        record.completed_at  = timezone.now()
        record.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
    except Exception as exc:
        record.status        = BackupRecord.Status.FAILED
        record.error_message = str(exc)[:2000]
        record.completed_at  = timezone.now()
        record.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
        logger.exception("Errore imprevisto durante il backup")

    return record


def restore_backup(backup_id, user):
    from apps.backups.models import BackupRecord
    from core.audit import log_action

    record = BackupRecord.objects.get(pk=backup_id)

    if record.status != BackupRecord.Status.COMPLETED:
        raise ValueError("Solo i backup completati possono essere ripristinati.")

    filepath = BACKUP_DIR / record.filename
    if not filepath.exists():
        raise FileNotFoundError(f"File non trovato sul server: {record.filename}")

    db = _db_params()
    env = os.environ.copy()
    env["PGPASSWORD"] = db["password"]

    cmd = [
        "pg_restore",
        "-h", db["host"],
        "-p", db["port"],
        "-U", db["user"],
        "-d", db["name"],
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        str(filepath),
    ]

    result = subprocess.run(
        cmd, env=env, capture_output=True, text=True, timeout=600
    )
    # pg_restore restituisce returncode=1 anche per warning non fatali
    # Consideriamo fallimento solo se non c'è output o stderr contiene ERROR
    if result.returncode > 1 or "ERROR" in result.stderr:
        raise RuntimeError(result.stderr[:2000] or "Errore sconosciuto durante il restore.")

    record.status = BackupRecord.Status.RESTORED
    record.save(update_fields=["status", "updated_at"])

    log_action(
        user=user,
        action_code="BACKUP_RESTORED",
        level="L3",
        entity=record,
        payload={"filename": record.filename},
    )
    logger.info("Restore completato da: %s", record.filename)


def delete_backup(backup_id, user):
    from apps.backups.models import BackupRecord
    from core.audit import log_action

    record = BackupRecord.objects.get(pk=backup_id)
    filepath = BACKUP_DIR / record.filename

    if filepath.exists():
        filepath.unlink()

    log_action(
        user=user,
        action_code="BACKUP_DELETED",
        level="L2",
        entity=record,
        payload={"filename": record.filename},
    )
    record.soft_delete()


def cleanup_old_backups() -> int:
    """Elimina file e record di backup più vecchi di 30 giorni. Restituisce il conteggio."""
    from apps.backups.models import BackupRecord

    cutoff = timezone.now() - timezone.timedelta(days=BACKUP_RETENTION_DAYS)
    old = BackupRecord.objects.filter(
        created_at__lt=cutoff,
        status=BackupRecord.Status.COMPLETED,
    )
    count = 0
    for rec in old:
        filepath = BACKUP_DIR / rec.filename
        if filepath.exists():
            filepath.unlink()
        rec.soft_delete()
        count += 1

    if count:
        logger.info("Cleanup: eliminati %d backup scaduti", count)
    return count

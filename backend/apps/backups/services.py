import logging
import os
import subprocess
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from . import encryption

logger = logging.getLogger("apps.backups")

BACKUP_DIR = Path(getattr(settings, "BACKUP_DIR", "/app/backups"))
BACKUP_RETENTION_DAYS = 30
# Suffisso applicato al file pg_dump dopo cifratura (newfix R4).
ENCRYPTED_SUFFIX = ".enc"


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
            # newfix F2 — il fallimento di un backup e' un evento privileged
            # (operazione di backup avviata da super_admin/scheduler) che deve
            # comparire nell'audit trail anche se non e' andato a buon fine.
            log_action(
                user=user,
                action_code="BACKUP_FAILED",
                level="L2",
                entity=record,
                payload={
                    "filename": record.filename,
                    "type": backup_type,
                    "error": (result.stderr or "")[:500],
                    "stage": "pg_dump",
                },
            )
        else:
            # newfix R4: cifratura at-rest se BACKUP_ENCRYPTION_KEY e' settata.
            encrypted = False
            if encryption.is_encryption_enabled():
                try:
                    enc_path = filepath.with_name(filepath.name + ENCRYPTED_SUFFIX)
                    encryption.encrypt_file(filepath, enc_path)
                    filepath = enc_path
                    record.filename = filepath.name
                    encrypted = True
                except Exception as exc:
                    record.status = BackupRecord.Status.FAILED
                    record.error_message = f"Cifratura fallita: {exc}"[:2000]
                    record.completed_at = timezone.now()
                    record.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
                    logger.exception("Cifratura backup fallita")
                    log_action(
                        user=user,
                        action_code="BACKUP_FAILED",
                        level="L2",
                        entity=record,
                        payload={
                            "filename": record.filename,
                            "type": backup_type,
                            "error": str(exc)[:500],
                            "stage": "encryption",
                        },
                    )
                    return record
            else:
                logger.warning(
                    "BACKUP_ENCRYPTION_KEY non configurata: backup salvato in chiaro. "
                    "In produzione e' obbligatorio cifrare (TISAX L3 / ISO 27001 A.8.24).",
                )

            size = filepath.stat().st_size if filepath.exists() else 0
            record.status       = BackupRecord.Status.COMPLETED
            record.size_bytes   = size
            record.completed_at = timezone.now()
            record.encrypted    = encrypted
            record.save(update_fields=["status", "size_bytes", "completed_at", "encrypted", "filename", "updated_at"])
            log_action(
                user=user,
                action_code="BACKUP_CREATED",
                level="L2",
                entity=record,
                payload={
                    "filename": record.filename, "size_bytes": size,
                    "type": backup_type, "encrypted": encrypted,
                },
            )
            logger.info("Backup completato: %s (%d bytes, encrypted=%s)", record.filename, size, encrypted)
    except subprocess.TimeoutExpired:
        record.status        = BackupRecord.Status.FAILED
        record.error_message = "Timeout: pg_dump ha impiegato più di 5 minuti."
        record.completed_at  = timezone.now()
        record.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
        log_action(
            user=user,
            action_code="BACKUP_FAILED",
            level="L2",
            entity=record,
            payload={
                "filename": record.filename,
                "type": backup_type,
                "error": "timeout_300s",
                "stage": "pg_dump",
            },
        )
    except Exception as exc:
        record.status        = BackupRecord.Status.FAILED
        record.error_message = str(exc)[:2000]
        record.completed_at  = timezone.now()
        record.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
        logger.exception("Errore imprevisto durante il backup")
        log_action(
            user=user,
            action_code="BACKUP_FAILED",
            level="L2",
            entity=record,
            payload={
                "filename": record.filename,
                "type": backup_type,
                "error": str(exc)[:500],
                "stage": "unexpected",
            },
        )

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

    # newfix R4: decifra in un file temporaneo prima del restore.
    plain_filepath = filepath
    decrypted_temp: Path | None = None
    if record.encrypted:
        decrypted_temp = filepath.with_suffix(filepath.suffix + ".restore")
        try:
            encryption.decrypt_file(filepath, decrypted_temp)
        except Exception as exc:
            # newfix F2 — fallimento restore (decifratura) e' privileged.
            log_action(
                user=user,
                action_code="BACKUP_RESTORE_FAILED",
                level="L3",
                entity=record,
                payload={
                    "filename": record.filename,
                    "error": str(exc)[:500],
                    "stage": "decryption",
                },
            )
            raise RuntimeError(f"Decifratura backup fallita: {exc}") from exc
        plain_filepath = decrypted_temp

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
        str(plain_filepath),
    ]

    try:
        result = subprocess.run(
            cmd, env=env, capture_output=True, text=True, timeout=600
        )
    finally:
        # Pulisci sempre il plain temporaneo, anche se pg_restore fallisce.
        if decrypted_temp is not None and decrypted_temp.exists():
            decrypted_temp.unlink()
    # pg_restore restituisce returncode=1 anche per warning non fatali
    # Consideriamo fallimento solo se non c'è output o stderr contiene ERROR
    if result.returncode > 1 or "ERROR" in result.stderr:
        # newfix F2 — fallimento restore (pg_restore) e' privileged.
        log_action(
            user=user,
            action_code="BACKUP_RESTORE_FAILED",
            level="L3",
            entity=record,
            payload={
                "filename": record.filename,
                "error": (result.stderr or "")[:500],
                "stage": "pg_restore",
            },
        )
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

import logging
import os
import subprocess
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from . import archive, encryption

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
    # Backup completo: archivio tar con il dump DB + l'albero MEDIA_ROOT.
    filename = f"backup_{ts}_{backup_type}.tar"
    filepath = BACKUP_DIR / filename
    # Il pg_dump viene scritto su un file temporaneo e poi impacchettato nel tar
    # insieme ai media; il temporaneo è rimosso a fine impacchettamento.
    dump_tmp = BACKUP_DIR / f"backup_{ts}_{backup_type}.dbtmp"

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
        "-f", str(dump_tmp),
    ]

    try:
        result = subprocess.run(
            cmd, env=env, capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0:
            dump_tmp.unlink(missing_ok=True)
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
            # Impacchetta dump DB + albero media in un unico tar, poi rimuove
            # il dump temporaneo. Da qui in avanti `filepath` è l'archivio.
            try:
                archive.build_archive(dump_tmp, filepath)
            except Exception as exc:
                dump_tmp.unlink(missing_ok=True)
                filepath.unlink(missing_ok=True)
                record.status        = BackupRecord.Status.FAILED
                record.error_message = f"Creazione archivio fallita: {exc}"[:2000]
                record.completed_at  = timezone.now()
                record.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
                logger.exception("Creazione archivio backup fallita")
                log_action(
                    user=user,
                    action_code="BACKUP_FAILED",
                    level="L2",
                    entity=record,
                    payload={
                        "filename": record.filename,
                        "type": backup_type,
                        "error": str(exc)[:500],
                        "stage": "archive",
                    },
                )
                return record
            finally:
                dump_tmp.unlink(missing_ok=True)

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


# Magic bytes del formato custom di pg_dump (-Fc): primo controllo di
# integrità sui file importati prima di accettarli come ripristinabili.
_PGDMP_MAGIC = b"PGDMP"


def import_backup(uploaded_file, user):
    """
    Importa un file di backup scaricato in precedenza (newfix F1).

    Accetta `.dump` (pg_dump custom format, verificato via magic PGDMP) o
    `.dump.enc` (cifrato GRC1/AES-GCM). I file cifrati vengono accettati solo
    se la BACKUP_ENCRYPTION_KEY corrente li decifra davvero: la probe fa una
    decifratura completa su file temporaneo e verifica il magic PGDMP del
    plaintext — così un import "buono" è garantito ripristinabile, invece di
    fallire al momento del restore (quando tipicamente c'è un'emergenza).

    Il filename su disco è sempre rigenerato (mai quello caricato): niente
    path traversal e niente collisioni. Il nome originale finisce in `notes`.

    Solleva ValueError con messaggio user-facing per ogni rifiuto.
    """
    from apps.backups.models import BackupRecord
    from core.audit import log_action

    _ensure_backup_dir()

    original_name = Path(getattr(uploaded_file, "name", "") or "").name
    lower = original_name.lower()
    if lower.endswith(".enc"):
        encrypted = True
        base = lower[: -len(".enc")]
    else:
        encrypted = False
        base = lower
    if base.endswith(".tar"):
        suffix = ".tar"
    elif base.endswith(".dump"):
        suffix = ".dump"
    else:
        raise ValueError(
            "Formato non supportato: sono ammessi solo file .tar, .tar.enc, .dump o .dump.enc."
        )

    max_bytes = getattr(settings, "BACKUP_IMPORT_MAX_BYTES", 2 * 1024**3)
    if uploaded_file.size > max_bytes:
        gb = max_bytes / 1024**3
        raise ValueError(f"File troppo grande. Dimensione massima per l'import: {gb:.1f} GB.")

    if encrypted and not encryption.is_encryption_enabled():
        raise ValueError(
            "Il file è cifrato ma BACKUP_ENCRYPTION_KEY non è configurata su "
            "questo server: impossibile verificarlo e ripristinarlo."
        )

    ts = timezone.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{ts}_imported{suffix}" + (ENCRYPTED_SUFFIX if encrypted else "")
    filepath = BACKUP_DIR / filename

    with open(filepath, "wb") as dest:
        for chunk in uploaded_file.chunks():
            dest.write(chunk)

    # Verifica del contenuto sul plaintext: archivio completo (tar con
    # database.dump) oppure dump pg_dump grezzo (legacy). In entrambi i casi
    # il dump deve iniziare col magic PGDMP, così un import accettato è
    # garantito ripristinabile.
    try:
        probe_path = None
        if encrypted:
            probe_path = filepath.with_name(filepath.name + ".probe")
            try:
                encryption.decrypt_file(filepath, probe_path)
            except Exception:
                raise ValueError(
                    "Il file cifrato non è decifrabile con la chiave configurata "
                    "su questo server (chiave diversa o file corrotto)."
                ) from None
            plain_for_check = probe_path
        else:
            plain_for_check = filepath

        try:
            if archive.is_full_archive(plain_for_check):
                head = archive.read_db_dump_head(plain_for_check)
            else:
                with open(plain_for_check, "rb") as f:
                    head = f.read(len(archive.PGDMP_MAGIC))
            if head != archive.PGDMP_MAGIC:
                raise ValueError(
                    "Il contenuto non è un backup valido (atteso archivio GRC "
                    "o dump pg_dump in formato custom)."
                )
        finally:
            if probe_path is not None and probe_path.exists():
                probe_path.unlink()
    except ValueError:
        # File rifiutato: non lasciare l'upload nella directory dei backup.
        if filepath.exists():
            filepath.unlink()
        raise

    size = filepath.stat().st_size
    record = BackupRecord.objects.create(
        filename=filename,
        status=BackupRecord.Status.COMPLETED,
        size_bytes=size,
        backup_type=BackupRecord.BackupType.IMPORTED,
        encrypted=encrypted,
        notes=f"Import manuale — file originale: {original_name[:200]}",
        completed_at=timezone.now(),
        created_by=user,
    )
    log_action(
        user=user,
        action_code="BACKUP_IMPORTED",
        level="L2",
        entity=record,
        payload={
            "filename": filename,
            "original_name": original_name[:200],
            "size_bytes": size,
            "encrypted": encrypted,
        },
    )
    logger.info("Backup importato: %s (%d bytes, encrypted=%s)", filename, size, encrypted)
    return record


def start_restore(backup_id, user):
    """
    Valida e accoda il restore su Celery (newfix 2026-06-09 #3).

    Il restore era sincrono nella request HTTP: pg_restore ha timeout 600s ma
    gunicorn killa il worker a 120s → su DB reali il processo moriva a metà
    `--clean` lasciando il DB incoerente. Ora la view marca il record come
    RESTORING e il lavoro vero avviene nel worker Celery (nessun timeout HTTP).

    Solleva ValueError/FileNotFoundError per le stesse pre-condizioni che
    prima bloccavano il restore sincrono.
    """
    from apps.backups.models import BackupRecord
    from apps.backups.tasks import restore_backup_task

    record = BackupRecord.objects.get(pk=backup_id)

    if record.status != BackupRecord.Status.COMPLETED:
        raise ValueError("Solo i backup completati possono essere ripristinati.")

    filepath = BACKUP_DIR / record.filename
    if not filepath.exists():
        raise FileNotFoundError(f"File non trovato sul server: {record.filename}")

    record.status = BackupRecord.Status.RESTORING
    record.error_message = ""
    record.save(update_fields=["status", "error_message", "updated_at"])

    restore_backup_task.delay(str(record.pk), str(user.pk))
    return record


def restore_backup(backup_id, user):
    from apps.backups.models import BackupRecord
    from core.audit import log_action

    record = BackupRecord.objects.get(pk=backup_id)

    # RESTORING = accodato da start_restore(); COMPLETED resta accettato per
    # invocazione diretta (shell/management) senza passare dalla coda.
    if record.status not in (
        BackupRecord.Status.COMPLETED, BackupRecord.Status.RESTORING,
    ):
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

    # Backup completo (tar) → estrai il dump DB e ripristina anche i media;
    # backup legacy (dump pg_dump grezzo) → ripristina il solo database.
    is_full = archive.is_full_archive(plain_filepath)
    db_dump_path = plain_filepath
    db_dump_temp: Path | None = None
    try:
        if is_full:
            db_dump_temp = plain_filepath.with_suffix(plain_filepath.suffix + ".dbrestore")
            try:
                archive.extract_db_dump(plain_filepath, db_dump_temp)
            except Exception as exc:
                log_action(
                    user=user,
                    action_code="BACKUP_RESTORE_FAILED",
                    level="L3",
                    entity=record,
                    payload={
                        "filename": record.filename,
                        "error": str(exc)[:500],
                        "stage": "archive_extract",
                    },
                )
                raise RuntimeError(f"Estrazione archivio fallita: {exc}") from exc
            db_dump_path = db_dump_temp

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
            str(db_dump_path),
        ]

        result = subprocess.run(
            cmd, env=env, capture_output=True, text=True, timeout=600
        )

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

        # DB ripristinato: ora rimpiazza l'albero media (swap atomico). Un
        # fallimento qui lascia il DB già ripristinato ma i media non allineati:
        # è un evento privileged e va segnalato senza fingere successo.
        if is_full:
            try:
                archive.restore_media(plain_filepath)
            except Exception as exc:
                log_action(
                    user=user,
                    action_code="BACKUP_RESTORE_FAILED",
                    level="L3",
                    entity=record,
                    payload={
                        "filename": record.filename,
                        "error": str(exc)[:500],
                        "stage": "media",
                    },
                )
                raise RuntimeError(
                    "Database ripristinato ma il ripristino dei file media è "
                    f"fallito: {exc}"
                ) from exc
    finally:
        # Pulisci sempre i temporanei, anche se il restore fallisce.
        if db_dump_temp is not None and db_dump_temp.exists():
            db_dump_temp.unlink()
        if decrypted_temp is not None and decrypted_temp.exists():
            decrypted_temp.unlink()

    record.status = BackupRecord.Status.RESTORED
    record.save(update_fields=["status", "updated_at"])

    log_action(
        user=user,
        action_code="BACKUP_RESTORED",
        level="L3",
        entity=record,
        payload={"filename": record.filename, "media_restored": is_full},
    )
    logger.info("Restore completato da: %s (media=%s)", record.filename, is_full)


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
    # newfix #13 — anche FAILED (file parziali di pg_dump interrotti) e
    # RESTORED rientrano nella retention: prima restavano su disco per sempre.
    # Esclusi solo gli stati transitori (running/pending/restoring).
    old = BackupRecord.objects.filter(
        created_at__lt=cutoff,
        status__in=[
            BackupRecord.Status.COMPLETED,
            BackupRecord.Status.FAILED,
            BackupRecord.Status.RESTORED,
        ],
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

import logging

from celery import shared_task

logger = logging.getLogger("apps.backups")


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def auto_backup_task(self):
    """Backup automatico giornaliero + cleanup backup scaduti."""
    try:
        from django.contrib.auth import get_user_model
        from apps.backups.services import create_backup, cleanup_old_backups

        User = get_user_model()
        user = User.objects.filter(is_superuser=True, is_active=True).order_by("date_joined").first()
        if user is None:
            logger.error("auto_backup_task: nessun superuser trovato, backup saltato.")
            return

        record = create_backup(user, backup_type="auto")
        cleaned = cleanup_old_backups()
        logger.info(
            "auto_backup_task completato: backup=%s status=%s, cleanup=%d",
            record.filename, record.status, cleaned,
        )
    except Exception as exc:
        logger.exception("auto_backup_task fallito")
        raise self.retry(exc=exc)


@shared_task
def restore_backup_task(backup_id: str, user_id: str):
    """
    Restore asincrono accodato da services.start_restore() (newfix 2026-06-09 #3).

    Nessun autoretry: un pg_restore fallito a metà non è idempotente — il
    retry automatico su un DB già parzialmente modificato peggiorerebbe le
    cose. In caso di errore il record torna COMPLETED con error_message
    valorizzato, e l'audit BACKUP_RESTORE_FAILED è già scritto dal service.
    """
    from django.contrib.auth import get_user_model
    from apps.backups.models import BackupRecord
    from apps.backups.services import restore_backup

    User = get_user_model()
    user = User.objects.filter(pk=user_id).first()

    try:
        restore_backup(backup_id, user)
    except Exception as exc:
        logger.exception("restore_backup_task fallito per backup %s", backup_id)
        record = BackupRecord.objects.filter(pk=backup_id).first()
        if record is not None:
            # Il file di backup è intatto: il record torna COMPLETED (riutilizzabile)
            # con l'errore visibile in UI.
            record.status = BackupRecord.Status.COMPLETED
            record.error_message = f"Restore fallito: {exc}"[:2000]
            record.save(update_fields=["status", "error_message", "updated_at"])

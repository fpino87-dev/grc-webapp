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

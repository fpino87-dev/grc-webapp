import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, default_retry_delay=300)
def cleanup_expired_audit_logs(self):
    """
    Elimina i log AuditTrail scaduti secondo la retention policy.
    L1: 5 anni, L2: 3 anni, L3: 1 anno.
    Eseguito il primo giorno di ogni mese.
    """
    from core.models import AuditLog

    now = timezone.now()
    retention = {
        "L1": now - timezone.timedelta(days=365 * 5),
        "L2": now - timezone.timedelta(days=365 * 3),
        "L3": now - timezone.timedelta(days=365 * 1),
    }

    total_deleted = 0
    for level, cutoff in retention.items():
        deleted, _ = AuditLog.objects.filter(
            level=level,
            timestamp_utc__lt=cutoff,
        ).delete()
        total_deleted += deleted
        if deleted:
            logger.info(
                "Audit log cleanup: eliminati %d record %s precedenti a %s",
                deleted, level, cutoff.date(),
            )

    return f"Cleanup completato: {total_deleted} record eliminati"


@shared_task
def cleanup_celery_results():
    """Elimina risultati task Celery più vecchi di 7 giorni."""
    from django_celery_results.models import TaskResult

    cutoff = timezone.now() - timezone.timedelta(days=7)
    deleted, _ = TaskResult.objects.filter(date_done__lt=cutoff).delete()
    return f"Celery results cleanup: {deleted} record eliminati"

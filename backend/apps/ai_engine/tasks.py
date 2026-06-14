"""Task Celery del modulo AI Engine."""
import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, default_retry_delay=300)
def cleanup_ai_interaction_logs(self):
    """Elimina i log di interazione AI più vecchi della retention configurata.

    L'output AI può contenere PII incidentale nel testo libero → non va conservato
    indefinitamente (GDPR Art. 5.1.e). Retention da `AI_LOG_RETENTION_DAYS`
    (default 365gg, override via settings/env). A differenza dell'AuditLog questo
    log NON è immutabile: la cancellazione per retention è ammessa e dovuta.
    """
    from apps.ai_engine.models import AiInteractionLog

    retention_days = getattr(settings, "AI_LOG_RETENTION_DAYS", 365)
    cutoff = timezone.now() - timezone.timedelta(days=retention_days)
    deleted, _ = AiInteractionLog.objects.filter(created_at__lt=cutoff).delete()
    if deleted:
        logger.info(
            "AI interaction log cleanup: eliminati %d record precedenti a %s",
            deleted, cutoff.date(),
        )
    return f"cleanup_ai_interaction_logs: {deleted} record eliminati"

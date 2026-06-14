import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

# NB: nessuna retention-by-deletion sull'AuditLog. È append-only e immutabile
# (trigger PostgreSQL `audit_no_mutation` blocca UPDATE/DELETE — regola #4):
# qualunque task di cancellazione fallirebbe e indebolirebbe la tamper-evidence
# e la linkage di catena. La conservazione è permanente; l'email è già
# pseudonimizzata in `log_action` (GDPR by design).


@shared_task
def cleanup_celery_results():
    """Elimina risultati task Celery più vecchi di 7 giorni."""
    from django_celery_results.models import TaskResult

    cutoff = timezone.now() - timezone.timedelta(days=7)
    deleted, _ = TaskResult.objects.filter(date_done__lt=cutoff).delete()
    return f"Celery results cleanup: {deleted} record eliminati"

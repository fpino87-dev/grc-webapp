from celery import shared_task
from django.utils import timezone
import datetime


@shared_task
def check_nis2_deadlines():
    """
    NIS2 requires notification within 24h for significant incidents.
    Escalates incidents that are nis2_notifiable='da_valutare' and older than 30 minutes.
    """
    from .models import Incident
    from core.audit import log_action

    cutoff = timezone.now() - datetime.timedelta(minutes=30)
    incidents = Incident.objects.filter(
        nis2_notifiable="da_valutare",
        status__in=["aperto", "in_analisi"],
        detected_at__lte=cutoff,
    )
    count = incidents.count()
    for incident in incidents:
        user = incident.created_by
        if user is not None:
            log_action(
                user=user,
                action_code="nis2_evaluation_overdue",
                level="L1",
                entity=incident,
                payload={"incident_id": str(incident.pk), "nis2_notifiable": incident.nis2_notifiable},
            )
    return f"Checked {count} NIS2 incidents"


@shared_task
def mark_overdue_incidents():
    """Mark incidents open > 72h as requiring attention"""
    from .models import Incident

    cutoff = timezone.now() - datetime.timedelta(hours=72)
    old_open = Incident.objects.filter(
        status="aperto",
        detected_at__lte=cutoff,
    )
    return f"Found {old_open.count()} overdue incidents"

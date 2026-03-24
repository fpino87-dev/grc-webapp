import datetime
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, retry_backoff=True)
def check_nis2_deadlines(self):
    """
    Ogni 30 minuti:
    1) escalation da_valutare > 30min
    2) alert scadenze T+24 / T+72 imminenti
    """
    from apps.tasks.services import create_task

    from .models import Incident

    now = timezone.now()
    today = now.date()
    count = 0

    cutoff = now - datetime.timedelta(minutes=30)
    overdue_eval = Incident.objects.filter(
        nis2_notifiable="da_valutare",
        status__in=["aperto", "in_analisi"],
        detected_at__lte=cutoff,
    ).select_related("plant")

    for inc in overdue_eval:
        create_task(
            plant=inc.plant,
            title=f"Classificare NIS2: {inc.title}",
            description=(
                "Incidente aperto da oltre 30 minuti senza classificazione NIS2.\n"
                f"Rilevato: {inc.detected_at.strftime('%d/%m/%Y %H:%M')}\n"
                "Aprire l'incidente e classificare la significativita."
            ),
            priority="critica",
            source_module="M09",
            source_id=inc.pk,
            due_date=today,
            assign_type="role",
            assign_value="compliance_officer",
        )
        count += 1

    threshold = now + datetime.timedelta(hours=4)
    sig_incidents = Incident.objects.filter(
        nis2_notifiable="si",
        status__in=["aperto", "in_analisi"],
    ).select_related("plant")

    for inc in sig_incidents:
        entity = inc.plant.nis2_scope if inc.plant else "importante"

        if entity == "essenziale" and inc.early_warning_deadline and now < inc.early_warning_deadline <= threshold:
            notified = inc.nis2_notifications.filter(notification_type="early_warning").exists()
            if not notified:
                hours_left = (inc.early_warning_deadline - now).total_seconds() / 3600
                create_task(
                    plant=inc.plant,
                    title=f"Early Warning NIS2 scade in {hours_left:.0f}h: {inc.title}",
                    priority="critica",
                    source_module="M09",
                    source_id=inc.pk,
                    due_date=inc.early_warning_deadline.date(),
                    assign_type="role",
                    assign_value="compliance_officer",
                )
                count += 1

        if inc.formal_notification_deadline and now < inc.formal_notification_deadline <= threshold:
            notified = inc.nis2_notifications.filter(notification_type="formal_notification").exists()
            if not notified:
                hours_left = (inc.formal_notification_deadline - now).total_seconds() / 3600
                create_task(
                    plant=inc.plant,
                    title=f"Notifica NIS2 scade in {hours_left:.0f}h: {inc.title}",
                    priority="critica",
                    source_module="M09",
                    source_id=inc.pk,
                    due_date=inc.formal_notification_deadline.date(),
                    assign_type="role",
                    assign_value="compliance_officer",
                )
                count += 1

    return f"check_nis2_deadlines: {count} task creati"


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, retry_backoff=True)
def check_final_report_deadlines(self):
    """Ogni giorno alle 09:00: alert report finale in scadenza (7gg e 1gg)."""
    from apps.tasks.services import create_task

    from .models import Incident

    today = timezone.now().date()
    count = 0

    for days_alert in (7, 1):
        target_date = today + datetime.timedelta(days=days_alert)
        incidents = Incident.objects.filter(
            nis2_notifiable="si",
            final_report_deadline=target_date,
        ).select_related("plant")

        for inc in incidents:
            notified = inc.nis2_notifications.filter(notification_type="final_report").exists()
            if notified:
                continue
            create_task(
                plant=inc.plant,
                title=f"Report Finale NIS2 scade in {days_alert}gg: {inc.title}",
                description=(
                    f"Il Report Finale NIS2 per l'incidente '{inc.title}' scade il {target_date}.\n"
                    "L'RCA deve essere approvato prima di generare il documento."
                ),
                priority="alta",
                source_module="M09",
                source_id=inc.pk,
                due_date=target_date,
                assign_type="role",
                assign_value="compliance_officer",
            )
            count += 1

    return f"check_final_report_deadlines: {count} task creati"

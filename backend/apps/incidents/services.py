from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError

from core.audit import log_action
from .models import Incident


def close_incident(incident: Incident, user):
    try:
        rca = incident.rca
    except Exception:
        rca = None
    if rca is None or rca.approved_at is None:
        raise ValidationError(_("RCA approvato obbligatorio per chiudere l'incidente."))

    if incident.is_significant:
        formal_sent = incident.nis2_notifications.filter(notification_type="formal_notification").exists()
        if not formal_sent:
            log_action(
                user=user,
                action_code="incident.closed_without_nis2_notification",
                level="L1",
                entity=incident,
                payload={
                    "warning": "Incidente NIS2 significativo chiuso senza notifica formale al CSIRT",
                    "incident_id": str(incident.pk),
                },
            )
            from apps.tasks.services import create_task

            create_task(
                plant=incident.plant,
                title=f"NIS2: notifica formale mancante — {incident.title}",
                description=(
                    f"L'incidente '{incident.title}' e stato chiuso senza aver inviato "
                    "la notifica formale NIS2 al CSIRT.\n"
                    f"Inviare il documento entro la scadenza: {incident.formal_notification_deadline}"
                ),
                priority="critica",
                source_module="M09",
                source_id=incident.pk,
                due_date=(
                    incident.formal_notification_deadline.date()
                    if incident.formal_notification_deadline
                    else timezone.now().date()
                ),
                assign_type="role",
                assign_value="compliance_officer",
            )

    incident.status = "chiuso"
    incident.closed_at = timezone.now()
    incident.closed_by = user
    incident.save(update_fields=["status", "closed_at", "closed_by", "updated_at"])

    # Feed M11 — crea PDCA automatico
    from apps.pdca.services import create_cycle
    create_cycle(
        plant=incident.plant,
        title=f"PDCA post-incidente: {incident.title}",
        trigger_type="incidente",
        trigger_source_id=incident.pk,
    )

    # Feed M12 — crea Lesson Learned
    from apps.lessons.models import LessonLearned
    LessonLearned.objects.create(
        plant=incident.plant,
        title=f"[Incidente] {incident.title}",
        description=rca.summary if rca else "",
        category="incident",
        source_module="M09",
        source_id=incident.pk,
        created_by=user,
        identified_by=user,
    )

    log_action(
        user=user,
        action_code="incident.closed",
        level="L1",
        entity=incident,
        payload={
            "incident_id": str(incident.pk),
            "nis2_notifiable": incident.nis2_notifiable,
            "severity": incident.severity,
        },
    )

    # Notifica NIS2 se applicabile
    if incident.nis2_notifiable == "si":
        try:
            from apps.notifications.resolver import fire_notification

            fire_notification(
                "incident_nis2",
                plant=incident.plant,
                context={"incident": incident},
            )
        except Exception:
            pass

    return incident

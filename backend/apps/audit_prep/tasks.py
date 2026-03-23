import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


def _task_exists(plant, source_module: str, source_id, title_prefix: str) -> bool:
    """
    Verifica se esiste già un task aperto con lo stesso source e titolo simile.
    Evita duplicati da run multipli del beat (riavvio Celery, task manuale, ecc.).
    """
    from apps.tasks.models import Task
    return Task.objects.filter(
        plant=plant,
        source_module=source_module,
        source_id=source_id,
        status__in=["aperto", "in_corso"],
        title__startswith=str(title_prefix)[:30],
    ).exists()


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def check_upcoming_audits(self):
    """
    Ogni lunedì alle 07:30.
    Controlla audit pianificati nel programma annuale e crea task di reminder.
    - 30 giorni prima: task preparazione al CO
    - 7 giorni prima: task urgente se AuditPrep non ancora aperto
    - Giorno dopo data pianificata: alert se non avviato
    """
    from .models import AuditProgram
    from apps.tasks.services import create_task
    from datetime import date

    today = timezone.now().date()
    created = 0

    programs = AuditProgram.objects.filter(
        status__in=["approvato", "in_corso"],
        deleted_at__isnull=True,
    ).select_related("plant")

    for program in programs:
        for audit in program.planned_audits:
            if audit.get("status") not in ("planned",):
                continue
            planned_date_str = audit.get("planned_date", "")
            if not planned_date_str:
                continue
            try:
                planned_date = date.fromisoformat(planned_date_str)
            except ValueError:
                continue

            days_left = (planned_date - today).days
            has_prep = bool(audit.get("audit_prep_id"))
            audit_title = audit.get("title", "Audit pianificato")
            quarter = audit.get("quarter", "?")

            if days_left == 30:
                prefix = f"Preparazione audit Q{quarter}"
                if not _task_exists(program.plant, "M17", program.pk, prefix):
                    create_task(
                        plant=program.plant,
                        title=f"Preparazione audit Q{quarter}: {audit_title}",
                        description=(
                            f"L'audit pianificato si svolgerà il "
                            f"{planned_date.strftime('%d/%m/%Y')}. "
                            f"Inizia la raccolta delle evidenze e "
                            f"verifica la disponibilità dell'auditor."
                        ),
                        priority="media",
                        source_module="M17",
                        source_id=program.pk,
                        due_date=planned_date,
                        assign_type="role",
                        assign_value="compliance_officer",
                    )
                    created += 1

            elif days_left == 7 and not has_prep:
                prefix = "⚠️ Avvia AuditPrep Q"
                if not _task_exists(program.plant, "M17", program.pk, prefix):
                    create_task(
                        plant=program.plant,
                        title=f"⚠️ Avvia AuditPrep Q{quarter}: {audit_title}",
                        description=(
                            f"Mancano 7 giorni all'audit del "
                            f"{planned_date.strftime('%d/%m/%Y')} "
                            f"e non è ancora stato aperto il prep. "
                            f"Vai in Audit Prep e clicca 'Avvia audit' sul programma."
                        ),
                        priority="alta",
                        source_module="M17",
                        source_id=program.pk,
                        due_date=planned_date,
                        assign_type="role",
                        assign_value="compliance_officer",
                    )
                    try:
                        from apps.notifications.resolver import fire_notification
                        fire_notification(
                            "audit_upcoming",
                            plant=program.plant,
                            context={"program": program, "audit": audit, "days_left": 7},
                        )
                    except Exception as e:
                        logger.warning("Notifica audit_upcoming fallita: %s", e)
                    created += 1

            elif days_left == -1 and not has_prep:
                prefix = "🚨 Audit Q"
                if not _task_exists(program.plant, "M17", program.pk, prefix):
                    create_task(
                        plant=program.plant,
                        title=f"🚨 Audit Q{quarter} non avviato: {audit_title}",
                        description=(
                            f"L'audit pianificato per il "
                            f"{planned_date.strftime('%d/%m/%Y')} "
                            f"non è stato avviato. "
                            f"Aprire subito un AuditPrep o segnare l'audit come annullato."
                        ),
                        priority="critica",
                        source_module="M17",
                        source_id=program.pk,
                        due_date=today + timezone.timedelta(days=3),
                        assign_type="role",
                        assign_value="compliance_officer",
                    )
                    created += 1

    return f"check_upcoming_audits: {created} task creati"


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def check_overdue_findings(self):
    """
    Ogni giorno alle 08:00.
    Finding aperti oltre la scadenza → task urgente.
    Notifica solo a 1, 7, 14 giorni di ritardo.
    """
    from .models import AuditFinding
    from apps.tasks.services import create_task

    today = timezone.now().date()
    created = 0

    overdue = AuditFinding.objects.filter(
        status__in=["open", "in_response"],
        response_deadline__lt=today,
        deleted_at__isnull=True,
    ).select_related("audit_prep__plant")

    for finding in overdue:
        days_overdue = (today - finding.response_deadline).days
        if days_overdue not in (1, 7, 14):
            continue
        prefix = "🚨 Finding scaduto"
        if not _task_exists(finding.audit_prep.plant, "M17", finding.pk, prefix):
            create_task(
                plant=finding.audit_prep.plant,
                title=f"🚨 Finding scaduto da {days_overdue}gg: {finding.title}",
                description=(
                    f"Tipo: {finding.finding_type.upper()}\n"
                    f"Scadenza: {finding.response_deadline.strftime('%d/%m/%Y')}\n"
                    f"Scaduto da: {days_overdue} giorni\n\n"
                    f"Completare la risposta e chiudere il finding."
                ),
                priority="critica",
                source_module="M17",
                source_id=finding.pk,
                due_date=today + timezone.timedelta(days=3),
                assign_type="role",
                assign_value="compliance_officer",
            )
            created += 1
            logger.info("Task finding scaduto creato: %d giorni", days_overdue)

    return f"check_overdue_findings: {created} task creati"


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def check_stale_audit_preps(self):
    """
    Ogni lunedì alle 08:15.
    AuditPrep in_corso da oltre 30 giorni senza aggiornamenti → reminder.
    """
    from .models import AuditPrep
    from apps.tasks.services import create_task

    threshold = timezone.now() - timezone.timedelta(days=30)
    created = 0

    stale = AuditPrep.objects.filter(
        status="in_corso",
        updated_at__lt=threshold,
        deleted_at__isnull=True,
    ).select_related("plant")

    for prep in stale:
        days_stale = (timezone.now() - prep.updated_at).days
        create_task(
            plant=prep.plant,
            title=f"Audit prep bloccato: {prep.title}",
            description=(
                f"L'audit prep '{prep.title}' è in corso da "
                f"{days_stale} giorni senza aggiornamenti. "
                f"Completarlo o annullarlo."
            ),
            priority="alta",
            source_module="M17",
            source_id=prep.pk,
            due_date=timezone.now().date() + timezone.timedelta(days=7),
            assign_type="role",
            assign_value="compliance_officer",
        )
        created += 1

    return f"check_stale_audit_preps: {created} task creati"

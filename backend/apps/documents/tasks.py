from celery import shared_task
from django.utils import timezone

from core.audit import log_action
from apps.auth_grc.models import GrcRole
from apps.tasks.services import create_task

from .services import (
    BLOCKING_TASK_STATUSES,
    OPEN_TASK_STATUSES,
    PENDING_STATUSES,
    REMINDER_SOURCE_MODULE,
)

# Giorni dalla creazione oltre i quali un documento obbligatorio ancora non
# approvato diventa un'attività assegnata (deciso in revisione documentale).
UNAPPROVED_REMINDER_DAYS = 90
# Prefisso stabile del titolo: identifica il promemoria "da approvare" fra i
# task M07 (gli altri riguardano le scadenze di revisione e validità).
UNAPPROVED_TITLE_PREFIX = "Documento obbligatorio da approvare: "


def _existing_reminders() -> set:
    """(documento, titolo) dei promemoria M07 già aperti o annullati.

    Il titolo distingue il tipo di promemoria (scadenza revisione, validità,
    documento da approvare) ed è stabile nel tempo: così un promemoria non si
    ripete ogni giorno, ma l'escalation "in scadenza" → "scaduto" resta
    possibile perché cambia titolo.
    """
    from apps.tasks.models import Task

    return set(
        Task.objects.filter(
            source_module=REMINDER_SOURCE_MODULE, status__in=BLOCKING_TASK_STATUSES,
        ).values_list("source_id", "title")
    )


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def notify_expiring_documents():
    """
    Giornaliero: controlla documenti con review_due_date o expiry_date
    in scadenza entro 30 giorni o già scaduti (una sola notifica per finestra).

    Finestre di notifica:
    - 30 giorni prima: avviso preventivo
    -  7 giorni prima: urgente
    - Già scaduto:     azione immediata richiesta

    Crea Task M08 sul compliance_officer del plant. Un promemoria per documento
    e per finestra: se ne esiste già uno aperto (o annullato da chi lo ha
    ricevuto) non se ne apre un altro — prima ne nasceva uno al giorno, per
    sempre, sullo stesso documento.
    """
    from django.contrib.auth import get_user_model
    from .models import Document

    User = get_user_model()
    system_user = User.objects.filter(is_superuser=True).first()
    today = timezone.localdate()

    WINDOWS = [
        (0,  7,  "alta",  "SCADUTO"),
        (8,  30, "media", "in scadenza"),
    ]

    task_count = 0
    existing = _existing_reminders()

    for field_name, field_label in [
        ("review_due_date", "revisione"),
        ("expiry_date", "validità"),
    ]:
        for low, high, priority, urgency_label in WINDOWS:
            date_high = today + timezone.timedelta(days=high)

            if low == 0:
                # scaduti: due_date < oggi
                docs = Document.objects.filter(
                    deleted_at__isnull=True,
                    status__in=["approvato", "bozza", "revisione", "approvazione"],
                    **{f"{field_name}__lt": today},
                ).select_related("plant", "owner")
            else:
                docs = Document.objects.filter(
                    deleted_at__isnull=True,
                    status__in=["approvato", "bozza", "revisione", "approvazione"],
                    **{
                        f"{field_name}__gte": today,
                        f"{field_name}__lte": date_high,
                    },
                ).select_related("plant", "owner")

            for doc in docs:
                due_date = getattr(doc, field_name)
                days_left = (due_date - today).days
                code_prefix = f"[{doc.document_code}] " if doc.document_code else ""

                if low == 0:
                    title = f"Documento {urgency_label} — scadenza {field_label}: {code_prefix}{doc.title}"
                    description = (
                        f"La scadenza di {field_label} del documento '{doc.document_code or doc.title}' "
                        f"era il {due_date} ({abs(days_left)} giorni fa). "
                        "Aggiorna o archivia il documento."
                    )
                    due_task = today + timezone.timedelta(days=7)
                else:
                    title = f"Documento {urgency_label} — scadenza {field_label}: {code_prefix}{doc.title}"
                    description = (
                        f"La scadenza di {field_label} del documento '{doc.document_code or doc.title}' "
                        f"è il {due_date} ({days_left} giorni). "
                        "Pianifica la revisione per tempo."
                    )
                    due_task = due_date - timezone.timedelta(days=3)

                if (doc.pk, title) in existing:
                    continue

                if system_user:
                    log_action(
                        user=system_user,
                        action_code="documents.expiry.reminder",
                        level="L1",
                        entity=doc,
                        payload={
                            "field": field_name,
                            "due_date": str(due_date),
                            "days_left": days_left,
                            "urgency": urgency_label,
                        },
                    )

                create_task(
                    plant=doc.plant,
                    title=title,
                    description=description,
                    priority=priority,
                    source_module="M07",
                    source_id=doc.pk,
                    due_date=due_task,
                    assign_type="role",
                    assign_value=GrcRole.COMPLIANCE_OFFICER,
                )
                existing.add((doc.pk, title))
                task_count += 1

    return f"notify_expiring_documents: {task_count} task creati"


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def remind_unapproved_mandatory_documents():
    """Giornaliero: un documento obbligatorio non approvato dopo
    UNAPPROVED_REMINDER_DAYS giorni dalla creazione diventa un'attività.

    Regola decisa con la direzione: un documento obbligatorio nasce, ha tre
    mesi per arrivare all'approvazione, poi la cosa non resta "da fare" ma
    viene assegnata a un ruolo (regola #7) e finisce nel riesame di direzione
    insieme agli altri documenti non approvati.

    Un solo promemoria per documento: non si ripete finché è aperto e non
    ricompare se chi lo riceve lo annulla. Si chiude da solo all'approvazione.
    """
    from django.contrib.auth import get_user_model
    from apps.tasks.models import Task
    from apps.tasks.services import complete_task
    from .models import Document

    User = get_user_model()
    system_user = User.objects.filter(is_superuser=True).first()
    today = timezone.localdate()
    cutoff = timezone.now() - timezone.timedelta(days=UNAPPROVED_REMINDER_DAYS)

    # 1) Promemoria rimasti aperti su documenti nel frattempo approvati o
    #    archiviati (p.es. se la chiusura contestuale all'approvazione è
    #    fallita): si chiudono qui.
    closed = 0
    if system_user:
        stale = Task.objects.filter(
            source_module=REMINDER_SOURCE_MODULE,
            status__in=OPEN_TASK_STATUSES,
            title__startswith=UNAPPROVED_TITLE_PREFIX,
        ).exclude(
            source_id__in=Document.objects.filter(
                deleted_at__isnull=True, status__in=PENDING_STATUSES,
            ).values("pk")
        )
        for task in stale:
            complete_task(task, system_user, notes="Documento non più in attesa di approvazione.")
            closed += 1

    # 2) Nuovi promemoria
    existing = _existing_reminders()
    docs = Document.objects.filter(
        deleted_at__isnull=True,
        is_mandatory=True,
        status__in=PENDING_STATUSES,
        created_at__lt=cutoff,
    ).select_related("plant", "owner")

    created = 0
    for doc in docs:
        code_prefix = f"[{doc.document_code}] " if doc.document_code else ""
        title = f"{UNAPPROVED_TITLE_PREFIX}{code_prefix}{doc.title}"
        if (doc.pk, title) in existing:
            continue

        age_days = (timezone.now() - doc.created_at).days
        description = (
            f"Il documento obbligatorio '{doc.document_code or doc.title}' è stato creato "
            f"{age_days} giorni fa ed è ancora in stato '{doc.get_status_display()}'.\n"
            "Portalo all'approvazione secondo il workflow documentale: il promemoria "
            "si chiude da solo quando il documento viene approvato.\n"
            "Finché resta non approvato compare fra i documenti da approvare del "
            "riesame di direzione."
        )
        if system_user:
            log_action(
                user=system_user,
                action_code="documents.approval.reminder",
                level="L1",
                entity=doc,
                payload={"status": doc.status, "age_days": age_days},
            )
        create_task(
            plant=doc.plant,
            title=title,
            description=description,
            priority="media",
            source_module=REMINDER_SOURCE_MODULE,
            source_id=doc.pk,
            due_date=today + timezone.timedelta(days=30),
            assign_type="role",
            assign_value=GrcRole.COMPLIANCE_OFFICER,
        )
        # Notifica M19 sull'evento già previsto "documento in attesa approvazione".
        try:
            from apps.notifications.resolver import fire_notification

            fire_notification("document_approval", plant=doc.plant, context={"document": doc})
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning(
                "Documento %s: notifica promemoria non inviata: %s", doc.pk, exc,
            )
        existing.add((doc.pk, title))
        created += 1

    return f"remind_unapproved_mandatory_documents: {created} task creati, {closed} chiusi"

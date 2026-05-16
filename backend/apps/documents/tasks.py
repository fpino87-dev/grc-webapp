from celery import shared_task
from django.utils import timezone

from core.audit import log_action
from apps.auth_grc.models import GrcRole
from apps.tasks.services import create_task


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

    Crea Task M08 sul compliance_officer del plant.
    """
    from django.contrib.auth import get_user_model
    from .models import Document

    User = get_user_model()
    system_user = User.objects.filter(is_superuser=True).first()
    today = timezone.now().date()

    WINDOWS = [
        (0,  7,  "alta",  "SCADUTO"),
        (8,  30, "media", "in scadenza"),
    ]

    task_count = 0

    for field_name, field_label in [
        ("review_due_date", "revisione"),
        ("expiry_date", "validità"),
    ]:
        for low, high, priority, urgency_label in WINDOWS:
            date_low = today - timezone.timedelta(days=low) if low == 0 else today + timezone.timedelta(days=low)
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
                    title = f"Documento {urgency_label} — scadenza {field_label} in {days_left}gg: {code_prefix}{doc.title}"
                    description = (
                        f"La scadenza di {field_label} del documento '{doc.document_code or doc.title}' "
                        f"è il {due_date} ({days_left} giorni). "
                        "Pianifica la revisione per tempo."
                    )
                    due_task = due_date - timezone.timedelta(days=3)

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
                task_count += 1

    return f"notify_expiring_documents: {task_count} task creati"

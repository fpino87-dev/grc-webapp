from celery import shared_task
from django.utils import timezone
import datetime


# Mappa category → ruolo responsabile
_CATEGORY_ROLE = {
    "control_review":           "control_owner",
    "control_audit":            "internal_auditor",
    "document_policy":          "compliance_officer",
    "document_procedure":       "compliance_officer",
    "document_record":          "compliance_officer",
    "risk_assessment":          "risk_manager",
    "risk_treatment":           "risk_manager",
    "bcp_test":                 "compliance_officer",
    "bcp_review":               "compliance_officer",
    "incident_review":          "compliance_officer",
    "supplier_assessment":      "compliance_officer",
    "supplier_contract_review": "compliance_officer",
    "training_mandatory":       "compliance_officer",
    "training_refresh":         "compliance_officer",
    "management_review":        "plant_manager",
    "security_committee":       "plant_manager",
    "finding_minor":            "internal_auditor",
    "finding_major":            "internal_auditor",
    "finding_observation":      "internal_auditor",
    "pdca_cycle":               "compliance_officer",
    "kpi_review":               "plant_manager",
    "isms_review":              "compliance_officer",
}


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def check_schedule_deadlines():
    """
    Eseguito ogni notte alle 02:30.
    Per ogni plant attivo, recupera le attività in scadenza (orizzonte 3 mesi).
    Per gli item urgency=red o yellow:
    - se non esiste già un task aperto per quell'item (dedup su source_id), crea un task in M08
    - assegna al ruolo responsabile per la categoria
    - priorità alta per red, media per yellow
    """
    from apps.plants.models import Plant
    from apps.tasks.models import Task
    from apps.tasks.services import create_task
    from core.audit import log_action
    from django.contrib.auth import get_user_model
    from .services import get_activity_schedule

    User = get_user_model()
    system_user = User.objects.filter(is_superuser=True).first()
    created = 0
    skipped = 0

    plants = Plant.objects.filter(deleted_at__isnull=True)

    for plant in plants:
        try:
            items = get_activity_schedule(plant=plant, months_ahead=3)
        except Exception:
            continue

        for item in items:
            if item.get("urgency") not in ("red", "yellow"):
                continue

            ref_id = item.get("ref_id")
            if not ref_id:
                continue

            # Dedup: non creare task se ne esiste già uno aperto per questo item
            already_open = Task.objects.filter(
                source_module="SCHED",
                source_id=ref_id,
                status__in=["aperto", "in_corso"],
                deleted_at__isnull=True,
            ).exists()
            if already_open:
                skipped += 1
                continue

            urgency = item["urgency"]
            days_left = item["days_left"]
            category = item.get("category", "")
            category_label = item.get("category_label", category)
            label = item.get("label", "")

            if days_left <= 0:
                urgency_note = "Scaduta"
            elif days_left == 1:
                urgency_note = "Scade domani"
            else:
                urgency_note = f"Scade tra {days_left} giorni"

            title = f"{category_label} — {urgency_note}"
            description = (
                f"{label}\n"
                f"Scadenza: {item['due_date']} ({urgency_note})\n"
                f"Categoria: {category_label}"
            )

            # Parsing due_date da stringa YYYY-MM-DD
            try:
                due_date = datetime.date.fromisoformat(item["due_date"])
            except (ValueError, KeyError):
                due_date = None

            priority = "alta" if urgency == "red" else "media"
            role = _CATEGORY_ROLE.get(category, "compliance_officer")

            try:
                task = create_task(
                    plant=plant,
                    title=title,
                    description=description,
                    priority=priority,
                    source_module="SCHED",
                    source_id=ref_id,
                    due_date=due_date,
                    assign_type="role",
                    assign_value=role,
                )
                created += 1

                if system_user:
                    log_action(
                        user=system_user,
                        action_code="schedule.task_created",
                        level="L1",
                        entity=task,
                        payload={
                            "category": category,
                            "urgency": urgency,
                            "due_date": item["due_date"],
                            "plant_id": str(plant.pk),
                            "ref_id": str(ref_id),
                        },
                    )
            except Exception:
                continue

    return f"check_schedule_deadlines: {created} task creati, {skipped} già esistenti"

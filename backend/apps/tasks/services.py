import datetime

from django.utils import timezone

from core.audit import log_action

from .models import Task


def create_task(
    plant,
    title,
    description="",
    priority="media",
    source_module="M03",
    source_id=None,
    due_date=None,
    assign_type=None,
    assign_value=None,
    control_instance=None,
):
    """Crea un Task collegato a un modulo sorgente."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    assigned_to = None
    if assign_type == "user" and assign_value:
        assigned_to = User.objects.filter(pk=assign_value).first()

    # Mappa source_module al campo source
    source_map = {
        "M03": "controllo", "M06": "rischio", "M09": "incidente",
        "M11": "pdca", "M17": "audit",
    }
    source = source_map.get(source_module, "manuale")

    return Task.objects.create(
        title=title,
        description=description,
        plant=plant,
        priority=priority,
        source=source,
        source_module=source_module or "",
        source_id=source_id,
        assigned_to=assigned_to,
        assigned_role=assign_value if assign_type == "role" else "",
        due_date=due_date,
        control_instance=control_instance,
    )


def complete_task(task, user, notes=""):
    task.status = "completato"
    task.completed_at = timezone.now()
    task.completed_by = user
    if notes:
        task.notes = (task.notes + "\n" + notes).strip()
    task.save(
        update_fields=["status", "completed_at", "completed_by", "notes", "updated_at"]
    )
    log_action(
        user=user,
        action_code="task.completed",
        level="L1",
        entity=task,
        payload={"id": str(task.pk), "title": task.title},
    )
    if task.recurrence != "none":
        _spawn_next_recurrence(task)


def _spawn_next_recurrence(task):
    deltas = {
        "daily": datetime.timedelta(days=1),
        "weekly": datetime.timedelta(weeks=1),
        "monthly": datetime.timedelta(days=30),
        "quarterly": datetime.timedelta(days=90),
        "yearly": datetime.timedelta(days=365),
    }
    delta = deltas.get(task.recurrence)
    if not delta or not task.due_date:
        return
    Task.objects.create(
        title=task.title,
        description=task.description,
        plant=task.plant,
        priority=task.priority,
        source=task.source,
        assigned_role=task.assigned_role,
        assigned_to=task.assigned_to,
        due_date=task.due_date + delta,
        recurrence=task.recurrence,
        parent_task=task,
        control_instance=task.control_instance,
        incident=task.incident,
    )


def escalate_task(task, user):
    task.escalation_level += 1
    task.escalated_at = timezone.now()
    task.save(update_fields=["escalation_level", "escalated_at", "updated_at"])
    log_action(
        user=user,
        action_code=f"task.escalated",
        level="L2",
        entity=task,
        payload={
            "id": str(task.pk),
            "title": task.title,
            "escalation_level": task.escalation_level,
        },
    )


def get_overdue_tasks(plant_id=None):
    qs = Task.objects.filter(
        status__in=["aperto", "in_corso"], due_date__lt=timezone.now().date()
    )
    if plant_id:
        qs = qs.filter(plant_id=plant_id)
    return qs.select_related("plant", "assigned_to")


# ── Quick Checklist (M08) ────────────────────────────────────────────────────

# Soglia: N run consecutivi incompleti su uno stesso template apre un PDCA (M11).
CHECKLIST_PDCA_THRESHOLD = 3


def _run_has_unchecked_mandatory(run) -> bool:
    """Vero se il run ha almeno un item obbligatorio non spuntato."""
    return run.items.filter(
        template_item__is_mandatory=True, checked=False
    ).exists()


def create_run_for_template(template, plant, due_date):
    """
    Crea un ChecklistRun per (template, plant, due_date) con un RunItem per
    ciascun item attivo del template. Idempotente: non duplica un run esistente.
    """
    from .models import ChecklistRun, ChecklistRunItem

    existing = ChecklistRun.objects.filter(
        template=template, plant=plant, due_date=due_date
    ).first()
    if existing:
        return existing

    run = ChecklistRun.objects.create(
        template=template,
        plant=plant,
        due_date=due_date,
        status="pending",
    )
    items = [
        ChecklistRunItem(run=run, template_item=ti)
        for ti in template.items.all()
    ]
    if items:
        ChecklistRunItem.objects.bulk_create(items)
    return run


def complete_run_item(run, item_id, checked, note="", user=None):
    """Spunta/de-spunta un singolo item del run. Nessun workflow, immediato."""
    run_item = run.items.filter(pk=item_id).first()
    if run_item is None:
        return None
    run_item.checked = bool(checked)
    run_item.note = note or ""
    if run_item.checked:
        run_item.checked_at = timezone.now()
        run_item.checked_by = user
    else:
        run_item.checked_at = None
        run_item.checked_by = None
    run_item.save(
        update_fields=["checked", "note", "checked_at", "checked_by", "updated_at"]
    )

    # Primo check → il run passa a in_progress
    if run.status == "pending" and run.items.filter(checked=True).exists():
        run.status = "in_progress"
        run.save(update_fields=["status", "updated_at"])
    return run_item


def complete_run(run, user):
    """
    Marca il run come completato — solo se tutti gli item obbligatori sono
    spuntati. Registra l'audit trail seguendo il pattern degli altri moduli.
    """
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    if _run_has_unchecked_mandatory(run):
        raise ValidationError(
            _("Tutti gli item obbligatori devono essere spuntati prima di completare.")
        )

    run.status = "completed"
    run.completed_at = timezone.now()
    run.completed_by = user
    run.save(update_fields=["status", "completed_at", "completed_by", "updated_at"])

    log_action(
        user=user,
        action_code="checklist_run.completed",
        level="L1",
        entity=run,
        payload={
            "id": str(run.pk),
            "template": run.template.name,
            "plant_id": str(run.plant_id),
            "items_total": run.items.count(),
            "items_checked": run.items.filter(checked=True).count(),
        },
    )
    return run


def evaluate_checklist_pdca_threshold(template, user=None):
    """
    Se gli ultimi CHECKLIST_PDCA_THRESHOLD run conclusi (completed/overdue) di
    un template hanno tutti almeno un item obbligatorio non spuntato, apre
    automaticamente un ciclo PDCA (M11) collegato al template.
    Idempotente: non crea un nuovo ciclo se ne esiste già uno aperto.
    """
    from apps.pdca.models import PdcaCycle
    from apps.pdca.services import create_cycle

    from .models import ChecklistRun

    recent = list(
        ChecklistRun.objects.filter(
            template=template, status__in=["completed", "overdue"]
        )
        .select_related("plant")
        .prefetch_related("items")
        .order_by("-due_date", "-created_at")[:CHECKLIST_PDCA_THRESHOLD]
    )
    if len(recent) < CHECKLIST_PDCA_THRESHOLD:
        return None
    if not all(_run_has_unchecked_mandatory(r) for r in recent):
        return None

    # Evita duplicati: un solo ciclo aperto per template alla volta.
    already_open = PdcaCycle.objects.filter(
        trigger_type="checklist_incompleta",
        trigger_source_id=template.pk,
        deleted_at__isnull=True,
    ).exclude(fase_corrente__in=["chiuso", "archiviato"]).exists()
    if already_open:
        return None

    plant = template.plant or recent[0].plant
    return create_cycle(
        plant=plant,
        title=f"Checklist ricorrente incompleta: {template.name}",
        trigger_type="checklist_incompleta",
        trigger_source_id=template.pk,
    )

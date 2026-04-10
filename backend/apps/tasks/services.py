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

from django.db import models
from django.contrib.auth import get_user_model
from core.models import BaseModel

User = get_user_model()


class Task(BaseModel):
    PRIORITY_CHOICES = [
        ("bassa", "Bassa"),
        ("media", "Media"),
        ("alta", "Alta"),
        ("critica", "Critica"),
    ]
    STATUS_CHOICES = [
        ("aperto", "Aperto"),
        ("in_corso", "In corso"),
        ("completato", "Completato"),
        ("annullato", "Annullato"),
        ("scaduto", "Scaduto"),
    ]
    SOURCE_CHOICES = [
        ("manuale", "Manuale"),
        ("controllo", "Controllo"),
        ("rischio", "Rischio"),
        ("incidente", "Incidente"),
        ("pdca", "PDCA"),
        ("audit", "Audit"),
    ]
    RECURRENCE_CHOICES = [
        ("none", "Nessuna"),
        ("daily", "Giornaliera"),
        ("weekly", "Settimanale"),
        ("monthly", "Mensile"),
        ("quarterly", "Trimestrale"),
        ("yearly", "Annuale"),
    ]

    source_module = models.CharField(max_length=10, blank=True, default="")
    source_id     = models.UUIDField(null=True, blank=True)

    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    plant = models.ForeignKey(
        "plants.Plant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="tasks",
        db_index=True,
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="media",
        db_index=True,
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default="aperto",
        db_index=True,
    )
    source = models.CharField(max_length=15, choices=SOURCE_CHOICES, default="manuale")

    assigned_role = models.CharField(max_length=50, blank=True)
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )
    due_date = models.DateField(null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_tasks",
    )

    # Relations to source objects
    control_instance = models.ForeignKey(
        "controls.ControlInstance",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    risk_assessment = models.ForeignKey(
        "risk.RiskAssessment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    incident = models.ForeignKey(
        "incidents.Incident",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )

    # Recurrence
    recurrence = models.CharField(
        max_length=15, choices=RECURRENCE_CHOICES, default="none"
    )
    parent_task = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recurrence_children",
    )

    # Escalation
    escalation_level = models.PositiveSmallIntegerField(default=0)
    escalated_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="escalated_tasks",
    )
    escalated_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["due_date", "-priority"]


class TaskComment(BaseModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    body = models.TextField()


# ── Quick Checklist (M08) ────────────────────────────────────────────────────
# Checklist operative ricorrenti: template riutilizzabili + run giornalieri
# generati automaticamente via Celery. Pensate per essere completate in 30s,
# senza workflow di approvazione.


class ChecklistTemplate(BaseModel):
    FREQUENCY_CHOICES = [
        ("daily", "Giornaliera"),
        ("weekly", "Settimanale"),
        ("monthly", "Mensile"),
        ("ad_hoc", "Ad hoc"),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    frequency = models.CharField(
        max_length=10, choices=FREQUENCY_CHOICES, default="daily", db_index=True
    )
    # plant null = template valido per tutti i plant
    plant = models.ForeignKey(
        "plants.Plant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="checklist_templates",
        db_index=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]


class ChecklistTemplateItem(BaseModel):
    template = models.ForeignKey(
        ChecklistTemplate, on_delete=models.CASCADE, related_name="items"
    )
    order = models.IntegerField(default=0)
    text = models.CharField(max_length=500)
    is_mandatory = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "created_at"]


class ChecklistRun(BaseModel):
    STATUS_CHOICES = [
        ("pending", "Da iniziare"),
        ("in_progress", "In corso"),
        ("completed", "Completata"),
        ("overdue", "Scaduta"),
    ]

    template = models.ForeignKey(
        ChecklistTemplate, on_delete=models.PROTECT, related_name="runs"
    )
    plant = models.ForeignKey(
        "plants.Plant",
        on_delete=models.PROTECT,
        related_name="checklist_runs",
        db_index=True,
    )
    # assegnazione diretta opzionale: i run auto-generati nascono senza assegnatario
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_checklist_runs",
    )
    due_date = models.DateField(db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_checklist_runs",
    )
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default="pending", db_index=True
    )

    class Meta:
        ordering = ["-due_date", "template__name"]


class ChecklistRunItem(BaseModel):
    run = models.ForeignKey(
        ChecklistRun, on_delete=models.CASCADE, related_name="items"
    )
    template_item = models.ForeignKey(
        ChecklistTemplateItem, on_delete=models.PROTECT, related_name="run_items"
    )
    checked = models.BooleanField(default=False)
    note = models.TextField(blank=True)
    checked_at = models.DateTimeField(null=True, blank=True)
    checked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="checked_checklist_items",
    )

    class Meta:
        ordering = ["template_item__order", "created_at"]

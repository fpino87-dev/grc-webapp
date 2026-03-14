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

    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    plant = models.ForeignKey(
        "plants.Plant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="tasks",
    )
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="media")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="aperto")
    source = models.CharField(max_length=15, choices=SOURCE_CHOICES, default="manuale")

    assigned_role = models.CharField(max_length=50, blank=True)
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )
    due_date = models.DateField(null=True, blank=True)
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

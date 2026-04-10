from django.db import models
from django.contrib.auth import get_user_model
from core.models import BaseModel

User = get_user_model()


class LessonLearned(BaseModel):
    STATUS_CHOICES = [("bozza", "Bozza"), ("validato", "Validato"), ("propagato", "Propagato")]
    CATEGORY_CHOICES = [
        ("incident", "Incidente"),
        ("audit", "Audit"),
        ("rischio", "Rischio"),
        ("operativo", "Operativo"),
        ("altro", "Altro"),
    ]

    title = models.CharField(max_length=300)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="altro")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="bozza")
    plant = models.ForeignKey("plants.Plant", on_delete=models.PROTECT, related_name="lessons")
    incident = models.ForeignKey(
        "incidents.Incident",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lessons",
    )
    identified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="identified_lessons",
    )
    validated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validated_lessons",
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    propagated_to_plants = models.ManyToManyField(
        "plants.Plant", blank=True, related_name="received_lessons"
    )
    corrective_action = models.TextField(blank=True)
    tags = models.JSONField(default=list)
    source_module = models.CharField(max_length=10, blank=True, default="")
    source_id = models.UUIDField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

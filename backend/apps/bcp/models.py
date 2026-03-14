from django.db import models
from django.contrib.auth import get_user_model
from core.models import BaseModel

User = get_user_model()


class BcpPlan(BaseModel):
    STATUS_CHOICES = [
        ("bozza", "Bozza"),
        ("approvato", "Approvato"),
        ("archiviato", "Archiviato"),
    ]
    plant = models.ForeignKey("plants.Plant", on_delete=models.PROTECT, related_name="bcp_plans")
    title = models.CharField(max_length=200)
    version = models.CharField(max_length=20, default="1.0")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="bozza")
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_bcps",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rto_hours = models.IntegerField(
        null=True, blank=True, help_text="Recovery Time Objective in hours"
    )
    rpo_hours = models.IntegerField(
        null=True, blank=True, help_text="Recovery Point Objective in hours"
    )
    last_test_date = models.DateField(null=True, blank=True)
    next_test_date = models.DateField(null=True, blank=True)
    critical_processes = models.ManyToManyField("bia.CriticalProcess", blank=True)
    critical_process = models.ForeignKey(
        "bia.CriticalProcess",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="bcp_plans",
    )
    content = models.JSONField(default=dict)

    class Meta:
        ordering = ["-created_at"]


class BcpTest(BaseModel):
    RESULT_CHOICES = [
        ("superato", "Superato"),
        ("parziale", "Parziale"),
        ("fallito", "Fallito"),
    ]
    plan = models.ForeignKey(BcpPlan, on_delete=models.CASCADE, related_name="tests")
    test_date = models.DateField()
    result = models.CharField(max_length=10, choices=RESULT_CHOICES)
    conducted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    lessons_id = models.UUIDField(null=True, blank=True)

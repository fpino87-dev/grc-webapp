from django.db import models
from django.contrib.auth import get_user_model
from core.models import BaseModel

User = get_user_model()


class AuditPrep(BaseModel):
    STATUS_CHOICES = [
        ("in_corso", "In corso"),
        ("completato", "Completato"),
        ("archiviato", "Archiviato"),
    ]
    plant = models.ForeignKey(
        "plants.Plant", on_delete=models.PROTECT, related_name="audit_preps"
    )
    framework = models.ForeignKey(
        "controls.Framework", on_delete=models.PROTECT, related_name="audit_preps"
    )
    title = models.CharField(max_length=200)
    audit_date = models.DateField(null=True, blank=True)
    auditor_name = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="in_corso")
    readiness_score = models.IntegerField(null=True, blank=True)
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class EvidenceItem(BaseModel):
    STATUS_CHOICES = [
        ("mancante", "Mancante"),
        ("presente", "Presente"),
        ("scaduto", "Scaduto"),
    ]
    audit_prep = models.ForeignKey(
        AuditPrep, on_delete=models.CASCADE, related_name="evidence_items"
    )
    control_instance = models.ForeignKey(
        "controls.ControlInstance", on_delete=models.SET_NULL, null=True, blank=True
    )
    description = models.CharField(max_length=300)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="mancante")
    document_id = models.UUIDField(null=True, blank=True)
    notes = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)

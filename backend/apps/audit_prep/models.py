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


class AuditFinding(BaseModel):
    FINDING_TYPE_CHOICES = [
        ("major_nc",    "Major Non Conformity"),
        ("minor_nc",    "Minor Non Conformity"),
        ("observation", "Observation"),
        ("opportunity", "Opportunity for Improvement"),
    ]
    STATUS_CHOICES = [
        ("open",                "Aperto"),
        ("in_response",         "In risposta"),
        ("closed",              "Chiuso"),
        ("accepted_by_auditor", "Accettato dall'auditor"),
    ]

    audit_prep = models.ForeignKey(
        AuditPrep, on_delete=models.CASCADE, related_name="findings"
    )
    control_instance = models.ForeignKey(
        "controls.ControlInstance",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="findings",
    )
    finding_type = models.CharField(max_length=20, choices=FINDING_TYPE_CHOICES)
    title = models.CharField(max_length=300)
    description = models.TextField()
    auditor_name = models.CharField(max_length=200, blank=True)
    audit_date = models.DateField()
    response_deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default="open")
    root_cause = models.TextField(blank=True)
    corrective_action = models.TextField(blank=True)

    pdca_cycle = models.ForeignKey(
        "pdca.PdcaCycle",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="findings",
    )
    closure_evidence = models.ForeignKey(
        "documents.Evidence",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="closed_findings",
    )
    closure_notes = models.TextField(blank=True)
    lesson_learned = models.ForeignKey(
        "lessons.LessonLearned",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="findings",
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        "auth.User", null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="closed_findings",
    )

    class Meta:
        ordering = ["-audit_date", "finding_type"]

    @property
    def is_overdue(self) -> bool:
        from django.utils import timezone
        if not self.response_deadline:
            return False
        return (
            self.status not in ("closed", "accepted_by_auditor")
            and self.response_deadline < timezone.now().date()
        )

    @property
    def days_remaining(self):
        from django.utils import timezone
        if not self.response_deadline:
            return None
        return (self.response_deadline - timezone.now().date()).days


class AuditProgram(BaseModel):
    """
    Programma annuale di audit interno.
    ISO 27001 clausola 9.2.
    """
    STATUS_CHOICES = [
        ("bozza",      "Bozza"),
        ("approvato",  "Approvato"),
        ("in_corso",   "In corso"),
        ("completato", "Completato"),
    ]

    plant = models.ForeignKey(
        "plants.Plant", on_delete=models.PROTECT,
        related_name="audit_programs"
    )
    year = models.IntegerField()
    framework = models.ForeignKey(
        "controls.Framework", on_delete=models.PROTECT,
        related_name="audit_programs"
    )
    title = models.CharField(max_length=200)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="bozza")
    objectives = models.TextField(blank=True)
    scope = models.TextField(blank=True)
    methodology = models.TextField(blank=True)

    # [{ "quarter": 1, "scope_domains": ["A.9"], "auditor_type": "interno|esterno",
    #    "auditor_name": "", "planned_date": "2026-03-15", "actual_date": null,
    #    "audit_prep_id": null, "status": "planned|completed|cancelled" }]
    planned_audits = models.JSONField(default=list)

    approved_by = models.ForeignKey(
        "auth.User", null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_audit_programs",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-year"]
        unique_together = ["plant", "framework", "year"]

    @property
    def completion_pct(self) -> float:
        total = len(self.planned_audits)
        completed = sum(1 for a in self.planned_audits if a.get("status") == "completed")
        return round(completed / total * 100, 1) if total > 0 else 0

    @property
    def next_planned_audit(self):
        from datetime import date
        today = str(date.today())
        upcoming = [
            a for a in self.planned_audits
            if a.get("status") == "planned" and a.get("planned_date", "") >= today
        ]
        return min(upcoming, key=lambda x: x.get("planned_date", ""), default=None)

from django.db import models
from core.models import BaseModel

# ─── Rule type catalogue ──────────────────────────────────────────────────────

RULE_TYPE_LABELS = {
    # Controls
    "control_review":           "Revisione controlli",
    "control_audit":            "Audit interno controlli",
    # Documents
    "document_policy":          "Revisione policy",
    "document_procedure":       "Revisione procedura",
    "document_record":          "Aggiornamento registro",
    # Risk
    "risk_assessment":          "Rivalutazione rischi",
    "risk_treatment":           "Revisione piano trattamento",
    # BCP
    "bcp_test":                 "Test BCP/DR",
    "bcp_review":               "Revisione piano BCP",
    # Incidents
    "incident_review":          "Revisione incidenti chiusi",
    # Suppliers
    "supplier_assessment":      "Assessment fornitori",
    "supplier_contract_review": "Revisione contratti fornitori",
    # Training
    "training_mandatory":       "Formazione obbligatoria",
    "training_refresh":         "Aggiornamento formazione",
    # Governance / Management Review
    "management_review":        "Revisione della direzione",
    "security_committee":       "Riunione comitato sicurezza",
    # Audit Prep
    "finding_minor":            "Risoluzione non conformità minore",
    "finding_major":            "Risoluzione non conformità maggiore",
    "finding_observation":      "Risoluzione osservazione",
    # PDCA
    "pdca_cycle":               "Ciclo PDCA",
    # KPI / Reporting
    "kpi_review":               "Revisione KPI",
    "isms_review":              "Revisione ISMS annuale",
}

RULE_CATEGORIES = {
    "Controlli": ["control_review", "control_audit"],
    "Documenti": ["document_policy", "document_procedure", "document_record"],
    "Rischi": ["risk_assessment", "risk_treatment"],
    "BCP": ["bcp_test", "bcp_review"],
    "Incidenti": ["incident_review"],
    "Fornitori": ["supplier_assessment", "supplier_contract_review"],
    "Formazione": ["training_mandatory", "training_refresh"],
    "Governance": ["management_review", "security_committee"],
    "Audit": ["finding_minor", "finding_major", "finding_observation"],
    "PDCA": ["pdca_cycle"],
    "Reporting": ["kpi_review", "isms_review"],
}

FREQUENCY_UNIT_CHOICES = [
    ("days",   "Giorni"),
    ("weeks",  "Settimane"),
    ("months", "Mesi"),
    ("years",  "Anni"),
]

# Default rules (frequency_value, frequency_unit, alert_days_before)
DEFAULT_RULES = {
    "control_review":           (1,  "years",  30),
    "control_audit":            (1,  "years",  60),
    "document_policy":          (1,  "years",  30),
    "document_procedure":       (2,  "years",  30),
    "document_record":          (1,  "years",  14),
    "risk_assessment":          (1,  "years",  45),
    "risk_treatment":           (6,  "months", 30),
    "bcp_test":                 (1,  "years",  30),
    "bcp_review":               (1,  "years",  30),
    "incident_review":          (3,  "months", 14),
    "supplier_assessment":      (1,  "years",  45),
    "supplier_contract_review": (1,  "years",  60),
    "training_mandatory":       (1,  "years",  30),
    "training_refresh":         (2,  "years",  60),
    "management_review":        (1,  "years",  30),
    "security_committee":       (3,  "months", 14),
    "finding_minor":            (90, "days",   14),
    "finding_major":            (30, "days",    7),
    "finding_observation":      (6,  "months", 30),
    "pdca_cycle":               (3,  "months", 14),
    "kpi_review":               (3,  "months", 14),
    "isms_review":              (1,  "years",  60),
}


# ─── Models ───────────────────────────────────────────────────────────────────

class ComplianceSchedulePolicy(BaseModel):
    """One active policy per plant (or global if plant is null)."""

    plant = models.ForeignKey(
        "plants.Plant",
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name="schedule_policies",
    )
    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateField()
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-valid_from"]

    def __str__(self):
        plant_label = self.plant.code if self.plant else "Globale"
        return f"{self.name} [{plant_label}]"

    def save(self, *args, **kwargs):
        # Deactivate previous active policy for same plant
        if self.is_active:
            qs = ComplianceSchedulePolicy.objects.filter(
                plant=self.plant, is_active=True
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            qs.update(is_active=False)
        super().save(*args, **kwargs)


class ScheduleRule(BaseModel):
    """One row per rule_type in a policy."""

    policy = models.ForeignKey(
        ComplianceSchedulePolicy,
        on_delete=models.CASCADE,
        related_name="rules",
    )
    rule_type = models.CharField(
        max_length=50,
        choices=[(k, v) for k, v in RULE_TYPE_LABELS.items()],
    )
    frequency_value = models.PositiveIntegerField()
    frequency_unit = models.CharField(max_length=10, choices=FREQUENCY_UNIT_CHOICES)
    alert_days_before = models.PositiveIntegerField(default=30)
    enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = [("policy", "rule_type")]

    def __str__(self):
        return f"{self.policy} — {self.rule_type} ({self.frequency_value} {self.frequency_unit})"


class RequiredDocument(BaseModel):
    """Mandatory document checklist entry per framework."""

    FRAMEWORK_CHOICES = [
        ("ISO27001",    "ISO 27001"),
        ("NIS2",        "NIS2"),
        ("TISAX_L2",    "TISAX L2"),
        ("TISAX_L3",    "TISAX L3"),
        ("TISAX_PROTO", "TISAX Prototype Protection"),
    ]

    framework = models.CharField(max_length=20, choices=FRAMEWORK_CHOICES)
    document_type = models.CharField(max_length=80)
    description = models.TextField()
    iso_clause = models.CharField(max_length=30, blank=True)
    mandatory = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["framework", "document_type"]

    def __str__(self):
        return f"[{self.framework}] {self.document_type}"

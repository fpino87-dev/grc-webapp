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

    TEST_FREQUENCY_UNIT_CHOICES = [
        ("days", "Giorni"),
        ("weeks", "Settimane"),
        ("months", "Mesi"),
        ("years", "Anni"),
    ]

    # Frequenza con cui il test BCP deve essere rieseguito.
    # La `next_test_date` viene calcolata a partire dalla data dell'ultimo test.
    test_frequency_value = models.PositiveIntegerField(default=1)
    test_frequency_unit = models.CharField(
        max_length=10,
        choices=TEST_FREQUENCY_UNIT_CHOICES,
        default="years",
    )

    class Meta:
        ordering = ["-created_at"]


class BcpTest(BaseModel):
    RESULT_CHOICES = [
        ("superato", "Superato"),
        ("parziale", "Parziale"),
        ("fallito", "Fallito"),
    ]
    TEST_TYPE_CHOICES = [
        ("tabletop", "Tabletop / Discussione"),
        ("drill", "Drill / Esercitazione parziale"),
        ("full_interruption", "Full interruption test"),
        ("parallel", "Test parallelo"),
    ]
    plan = models.ForeignKey(BcpPlan, on_delete=models.CASCADE, related_name="tests")
    test_date = models.DateField()
    result = models.CharField(max_length=10, choices=RESULT_CHOICES)
    conducted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    lessons_id = models.UUIDField(null=True, blank=True)

    # Structured test data
    test_type = models.CharField(
        max_length=20, choices=TEST_TYPE_CHOICES, default="tabletop"
    )
    objectives = models.JSONField(
        default=list,
        help_text='List of {"text": str, "met": bool} objects',
    )
    rto_achieved_hours = models.IntegerField(
        null=True, blank=True,
        help_text="Actual RTO achieved during this test (hours)",
    )
    rpo_achieved_hours = models.IntegerField(
        null=True, blank=True,
        help_text="Actual RPO achieved during this test (hours)",
    )
    participants_count = models.IntegerField(default=0)

    # Evidenze collegate al test BCP (es. output del test, report, screenshot, ecc.)
    # Le evidenze sono gestite dal modulo documents.Evidence.
    evidences = models.ManyToManyField(
        "documents.Evidence",
        blank=True,
        related_name="bcp_tests",
    )

    @property
    def objectives_met_pct(self) -> float | None:
        """Percentage of objectives marked as met. None if no objectives defined."""
        if not self.objectives:
            return None
        met = sum(1 for o in self.objectives if o.get("met"))
        return round(met / len(self.objectives) * 100, 1)

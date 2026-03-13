from django.db import models

from core.models import BaseModel


class CriticalProcess(BaseModel):
    plant = models.ForeignKey("plants.Plant", on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    owner = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    criticality = models.IntegerField(default=3)
    status = models.CharField(
        max_length=20,
        choices=[("bozza", "Bozza"), ("validato", "Validato"), ("approvato", "Approvato")],
        default="bozza",
    )
    downtime_cost_hour = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )
    fatturato_esposto_anno = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True,
    )
    danno_reputazionale = models.IntegerField(default=1)
    danno_normativo = models.IntegerField(default=1)
    danno_operativo = models.IntegerField(default=1)
    validated_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="validated_processes",
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_processes",
    )
    approved_at = models.DateTimeField(null=True, blank=True)


class TreatmentOption(BaseModel):
    process = models.ForeignKey(
        CriticalProcess,
        on_delete=models.CASCADE,
        related_name="treatment_options",
    )
    title = models.CharField(max_length=200)
    cost_implementation = models.DecimalField(max_digits=14, decimal_places=2)
    cost_annual = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    ale_reduction_pct = models.FloatField()


class RiskDecision(BaseModel):
    process = models.ForeignKey(
        CriticalProcess,
        on_delete=models.CASCADE,
        related_name="risk_decisions",
    )
    decision = models.CharField(
        max_length=20,
        choices=[
            ("accettare", "Accettare"),
            ("mitigare", "Mitigare"),
            ("trasferire", "Trasferire"),
            ("evitare", "Evitare"),
        ],
    )
    rationale = models.TextField()
    decided_by = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    decided_at = models.DateTimeField(auto_now_add=True)
    review_by = models.DateField()
    treatment = models.ForeignKey(
        TreatmentOption,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )


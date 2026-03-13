from django.db import models

from core.models import BaseModel


PROB_MAP = {1: 0.1, 2: 0.3, 3: 1.0, 4: 3.0, 5: 10.0}
IMPACT_MAP = {1: 0.05, 2: 0.20, 3: 0.40, 4: 0.70, 5: 1.0}


class RiskAssessment(BaseModel):
    plant = models.ForeignKey("plants.Plant", on_delete=models.CASCADE)
    asset = models.ForeignKey(
        "assets.Asset",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    assessment_type = models.CharField(
        max_length=5,
        choices=[("IT", "IT"), ("OT", "OT")],
    )
    status = models.CharField(
        max_length=20,
        choices=[("bozza", "Bozza"), ("completato", "Completato"), ("archiviato", "Archiviato")],
        default="bozza",
    )
    assessed_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    assessed_at = models.DateTimeField(null=True, blank=True)
    score = models.IntegerField(null=True, blank=True)
    ale_annuo = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    risk_accepted = models.BooleanField(default=False)
    accepted_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="accepted_risks",
    )
    plan_due_date = models.DateField(null=True, blank=True)

    @property
    def risk_level(self):
        if self.score is None:
            return None
        if self.score <= 7:
            return "verde"
        if self.score <= 14:
            return "giallo"
        return "rosso"


class RiskDimension(BaseModel):
    assessment = models.ForeignKey(
        RiskAssessment,
        on_delete=models.CASCADE,
        related_name="dimensions",
    )
    dimension_code = models.CharField(max_length=50)
    value = models.IntegerField()
    notes = models.TextField(blank=True)


class RiskMitigationPlan(BaseModel):
    assessment = models.ForeignKey(
        RiskAssessment,
        on_delete=models.CASCADE,
        related_name="mitigation_plans",
    )
    action = models.TextField()
    owner = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    due_date = models.DateField()
    completed_at = models.DateTimeField(null=True, blank=True)
    control_instance = models.ForeignKey(
        "controls.ControlInstance",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )


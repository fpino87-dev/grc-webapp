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

    # BCP/BIA targets — ISO 22301 & TISAX
    mtpd_hours = models.IntegerField(
        null=True, blank=True,
        help_text="Maximum Tolerable Period of Disruption (hours)",
    )
    mbco_pct = models.IntegerField(
        null=True, blank=True,
        help_text="Minimum Business Continuity Objective — % of normal capacity",
    )
    rto_target_hours = models.IntegerField(
        null=True, blank=True,
        help_text="Recovery Time Objective target (hours)",
    )
    rpo_target_hours = models.IntegerField(
        null=True, blank=True,
        help_text="Recovery Point Objective target (hours)",
    )

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

    @property
    def bia_targets_complete(self) -> bool:
        """True when all four BIA/BCP targets have been set."""
        return all(
            v is not None
            for v in [self.mtpd_hours, self.mbco_pct, self.rto_target_hours, self.rpo_target_hours]
        )

    @property
    def rto_bcp_status(self) -> str:
        """
        Compare rto_target_hours against the best BCP plan RTO for this process.
        Returns: 'ok' | 'warning' | 'critical' | 'unknown'
        """
        if self.rto_target_hours is None:
            return "unknown"
        from apps.bcp.models import BcpPlan

        # Considera solo piani BCP approvati: per la UX deve essere chiaro
        # che "BCP ok/warning/critical" dipende dal piano approvato.
        direct_best = (
            self.bcp_plans.filter(
                deleted_at__isnull=True,
                status="approvato",
                rto_hours__isnull=False,
            )
            .order_by("rto_hours")
            .first()
        )
        m2m_best = (
            BcpPlan.objects.filter(
                deleted_at__isnull=True,
                status="approvato",
                rto_hours__isnull=False,
                critical_processes=self,
            )
            .order_by("rto_hours")
            .first()
        )

        candidates = [c for c in [direct_best, m2m_best] if c is not None]
        best_bcp = min(candidates, key=lambda c: c.rto_hours) if candidates else None
        if best_bcp is None:
            return "unknown"

        ratio = best_bcp.rto_hours / self.rto_target_hours
        if ratio <= 1.0:
            return "ok"
        elif ratio <= 1.5:
            return "warning"
        return "critical"


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


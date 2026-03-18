from django.db import models

from core.models import BaseModel


PROB_MAP = {1: 0.1, 2: 0.3, 3: 1.0, 4: 3.0, 5: 10.0}
IMPACT_MAP = {1: 0.05, 2: 0.20, 3: 0.40, 4: 0.70, 5: 1.0}


THREAT_CATEGORIES = [
    ("accesso_non_autorizzato", "Accesso non autorizzato"),
    ("malware_ransomware", "Malware / Ransomware"),
    ("data_breach", "Data breach / Fuga di dati"),
    ("phishing_social", "Phishing / Social engineering"),
    ("guasto_hw_sw", "Guasto hardware / software"),
    ("disastro_naturale", "Disastro naturale / ambientale"),
    ("errore_umano", "Errore umano"),
    ("attacco_supply_chain", "Attacco supply chain"),
    ("ddos", "DoS / DDoS"),
    ("insider_threat", "Insider threat"),
    ("furto_perdita", "Furto / perdita dispositivi"),
    ("altro", "Altro"),
]

PROB_CHOICES = [(1,"1 – Molto bassa"),(2,"2 – Bassa"),(3,"3 – Media"),(4,"4 – Alta"),(5,"5 – Molto alta")]
IMPACT_CHOICES = [(1,"1 – Trascurabile"),(2,"2 – Minore"),(3,"3 – Moderato"),(4,"4 – Grave"),(5,"5 – Critico")]
TREATMENT_CHOICES = [("mitigare","Mitigare"),("accettare","Accettare"),("trasferire","Trasferire"),("evitare","Evitare")]


class RiskScenario(BaseModel):
    """
    Nodo centrale scenario di rischio (plant + processo + asset + minaccia).
    Leggero e retro-compatibile: non sostituisce RiskAssessment ma lo affianca.
    """
    plant = models.ForeignKey(
        "plants.Plant",
        on_delete=models.CASCADE,
        related_name="risk_scenarios",
    )
    critical_process = models.ForeignKey(
        "bia.CriticalProcess",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="risk_scenarios",
    )
    asset = models.ForeignKey(
        "assets.Asset",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="risk_scenarios",
    )
    threat_category = models.CharField(
        max_length=50,
        blank=True,
        default="",
        choices=THREAT_CATEGORIES,
    )
    likelihood = models.IntegerField(
        null=True,
        blank=True,
        choices=PROB_CHOICES,
        help_text="Probabilità scenario (1-5)",
    )
    impact = models.IntegerField(
        null=True,
        blank=True,
        choices=IMPACT_CHOICES,
        help_text="Impatto scenario (1-5)",
    )
    risk_score = models.IntegerField(
        null=True,
        blank=True,
        help_text="Score scenario = likelihood × impact",
    )

    class Meta:
        ordering = ["-created_at"]


class RiskAssessment(BaseModel):
    plant = models.ForeignKey("plants.Plant", on_delete=models.CASCADE)
    asset = models.ForeignKey(
        "assets.Asset",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="risk_assessments",
    )
    name = models.CharField(max_length=200, blank=True, default="")
    threat_category = models.CharField(max_length=50, blank=True, default="", choices=THREAT_CATEGORIES)
    assessment_type = models.CharField(
        max_length=5,
        choices=[("IT", "IT"), ("OT", "OT")],
        db_index=True,
    )
    probability = models.IntegerField(null=True, blank=True, choices=PROB_CHOICES)
    impact = models.IntegerField(null=True, blank=True, choices=IMPACT_CHOICES)
    treatment = models.CharField(max_length=20, blank=True, default="", choices=TREATMENT_CHOICES)
    status = models.CharField(
        max_length=20,
        choices=[("bozza", "Bozza"), ("completato", "Completato"), ("archiviato", "Archiviato")],
        default="bozza",
        db_index=True,
    )
    assessed_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    owner = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_risks",
        help_text="Responsabile del rischio (diverso da chi lo ha valutato)",
    )
    assessed_at = models.DateTimeField(null=True, blank=True)
    score = models.IntegerField(null=True, blank=True, db_index=True)
    ale_annuo = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    needs_revaluation = models.BooleanField(
        default=False,
        help_text="True se un change recente richiede rivalutazione",
    )
    needs_revaluation_since = models.DateField(null=True, blank=True)

    risk_accepted = models.BooleanField(default=False)
    accepted_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="accepted_risks",
    )
    plan_due_date = models.DateField(null=True, blank=True)

    # Rischio inerente (PRIMA dei controlli)
    inherent_probability = models.IntegerField(
        null=True, blank=True,
        choices=PROB_CHOICES,
        help_text="Probabilità senza considerare i controlli esistenti",
    )
    inherent_impact = models.IntegerField(
        null=True, blank=True,
        choices=IMPACT_CHOICES,
        help_text="Impatto senza considerare i controlli esistenti",
    )
    inherent_score = models.IntegerField(
        null=True, blank=True,
        help_text="Score inerente = inherent_prob × inherent_impact",
    )

    # Accettazione formale del rischio residuo
    risk_accepted_formally = models.BooleanField(default=False)
    risk_accepted_by = models.ForeignKey(
        "auth.User",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="formally_accepted_risks",
    )
    risk_accepted_at = models.DateTimeField(null=True, blank=True)
    risk_acceptance_note = models.TextField(blank=True)
    risk_acceptance_expiry = models.DateField(
        null=True, blank=True,
        help_text="Data scadenza accettazione rischio — va rinnovata",
    )
    critical_process = models.ForeignKey(
        "bia.CriticalProcess",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="risk_assessments",
    )

    def save(self, *args, **kwargs):
        if self.probability and self.impact:
            self.score = self.probability * self.impact
        if self.inherent_probability and self.inherent_impact:
            self.inherent_score = self.inherent_probability * self.inherent_impact
        super().save(*args, **kwargs)

    @property
    def risk_level(self):
        s = self.weighted_score or self.score
        if s is None:
            return None
        if s <= 7:
            return "verde"
        if s <= 14:
            return "giallo"
        return "rosso"

    @property
    def inherent_risk_level(self):
        s = self.inherent_score or 0
        if s <= 7:
            return "verde"
        if s <= 14:
            return "giallo"
        return "rosso"

    @property
    def residual_score(self):
        """Alias esplicito — il campo score è il rischio residuo."""
        return self.score

    @property
    def risk_reduction_pct(self):
        """Percentuale di riduzione del rischio grazie ai controlli."""
        if not self.inherent_score or not self.score:
            return None
        if self.inherent_score == 0:
            return 0
        return round((self.inherent_score - self.score) / self.inherent_score * 100, 1)

    @property
    def weighted_score(self):
        """Score tecnico pesato per criticità BIA."""
        if self.score is None:
            return None
        multipliers = {1: 1.0, 2: 1.0, 3: 1.2, 4: 1.5, 5: 2.0}
        crit = getattr(self.critical_process, "criticality", 3)
        return min(25, round(self.score * multipliers.get(crit, 1.0)))


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
    # Collega il piano di mitigazione a un BCP: la mitigazione vale finché il BCP
    # resta "valid" (next_test_date >= oggi) e quindi può perdere valore
    # automaticamente quando il test BCP scade.
    bcp_plan = models.ForeignKey(
        "bcp.BcpPlan",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="risk_mitigation_plans",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    control_instance = models.ForeignKey(
        "controls.ControlInstance",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )


class RiskAppetitePolicy(BaseModel):
    """
    Soglie di accettazione del rischio approvate dal management.
    ISO 27001 clausola 6.1.2 / NIS2 Art. 21.
    """
    plant = models.ForeignKey(
        "plants.Plant",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="risk_appetite_policies",
        help_text="Null = policy org-wide valida per tutti i plant"
    )
    framework_code = models.CharField(
        max_length=50, blank=True,
        help_text="Blank = valida per tutti i framework"
    )
    max_acceptable_score = models.IntegerField(
        default=14,
        help_text="Score massimo accettabile senza PDCA obbligatorio."
    )
    max_red_risks_count = models.IntegerField(
        default=3,
        help_text="Numero massimo di rischi rossi tollerabili contemporaneamente."
    )
    max_unacceptable_score = models.IntegerField(
        default=20,
        help_text="Score oltre il quale il rischio NON puo' essere solo accettato."
    )
    review_frequency_months = models.IntegerField(default=12)
    valid_from = models.DateField()
    valid_until = models.DateField(null=True, blank=True)
    approved_by = models.ForeignKey(
        "auth.User", null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_risk_policies",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-valid_from"]

    @property
    def is_active(self):
        from django.utils import timezone
        today = timezone.now().date()
        return (
            self.valid_from <= today and
            (self.valid_until is None or self.valid_until >= today)
        )


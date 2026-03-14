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


class RiskAssessment(BaseModel):
    plant = models.ForeignKey("plants.Plant", on_delete=models.CASCADE)
    asset = models.ForeignKey(
        "assets.Asset",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    name = models.CharField(max_length=200, blank=True, default="")
    threat_category = models.CharField(max_length=50, blank=True, default="", choices=THREAT_CATEGORIES)
    assessment_type = models.CharField(
        max_length=5,
        choices=[("IT", "IT"), ("OT", "OT")],
    )
    probability = models.IntegerField(null=True, blank=True, choices=PROB_CHOICES)
    impact = models.IntegerField(null=True, blank=True, choices=IMPACT_CHOICES)
    treatment = models.CharField(max_length=20, blank=True, default="", choices=TREATMENT_CHOICES)
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

    def save(self, *args, **kwargs):
        if self.probability and self.impact:
            self.score = self.probability * self.impact
        super().save(*args, **kwargs)

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


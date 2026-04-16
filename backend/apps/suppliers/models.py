from django.db import models
from django.contrib.auth import get_user_model
from core.models import BaseModel

User = get_user_model()


class Supplier(BaseModel):
    RISK_CHOICES = [
        ("basso", "Basso"),
        ("medio", "Medio"),
        ("alto", "Alto"),
        ("critico", "Critico"),
    ]
    STATUS_CHOICES = [
        ("attivo", "Attivo"),
        ("sospeso", "Sospeso"),
        ("terminato", "Terminato"),
    ]
    NIS2_CRITERION_CHOICES = [
        ("ict", "Fornitura ICT strutturale (criterio a)"),
        ("non_fungibile", "Non fungibilità (criterio b)"),
        ("entrambi", "Entrambi (a + b)"),
    ]

    name = models.CharField(max_length=200)
    vat_number = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=2, default="IT")
    description = models.TextField(blank=True)
    risk_level = models.CharField(max_length=10, choices=RISK_CHOICES, default="medio")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="attivo")
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_suppliers",
    )
    plants = models.ManyToManyField("plants.Plant", blank=True, related_name="suppliers")
    framework_refs = models.JSONField(default=list)
    notes = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    evaluation_date = models.DateField(null=True, blank=True)

    # Campi ACN Delibera 127434 del 13/04/2026
    cpv_codes = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista di oggetti {code, label} — Codici CPV della fornitura",
    )
    nis2_relevant = models.BooleanField(
        default=False,
        help_text="Fornitore rilevante ai fini NIS2 (ACN Delibera 127434)",
    )
    nis2_relevance_criterion = models.CharField(
        max_length=20,
        blank=True,
        choices=NIS2_CRITERION_CHOICES,
        help_text="Criterio di rilevanza NIS2: ICT strutturale (a), non fungibilità (b), o entrambi",
    )
    supply_concentration_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="% di concentrazione della fornitura — soglia TPRM: <20% bassa, 20-50% media, >50% critica",
    )

    class Meta:
        ordering = ["name"]

    @property
    def concentration_threshold(self) -> str:
        """Soglia TPRM derivata dalla % di concentrazione (ACN Delibera 127434)."""
        if self.supply_concentration_pct is None:
            return "nd"
        pct = float(self.supply_concentration_pct)
        if pct < 20:
            return "bassa"
        if pct <= 50:
            return "media"
        return "critica"


class SupplierAssessment(BaseModel):
    APPROVAL_CHOICES = [
        ("pianificato", "Pianificato"),
        ("in_corso", "In corso"),
        ("completato", "Completato"),
        ("approvato", "Approvato"),
        ("rifiutato", "Rifiutato"),
    ]
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="assessments")
    assessed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    assessment_date = models.DateField()
    status = models.CharField(
        max_length=15,
        choices=APPROVAL_CHOICES,
        default="pianificato",
    )
    # Campi approvazione
    reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_supplier_assessments",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)

    # Score strutturato
    score_governance = models.IntegerField(null=True, blank=True)
    score_security = models.IntegerField(null=True, blank=True)
    score_bcp = models.IntegerField(null=True, blank=True)
    score_overall = models.IntegerField(null=True, blank=True)
    score = models.IntegerField(null=True, blank=True)

    findings = models.TextField(blank=True)
    next_assessment_date = models.DateField(null=True, blank=True)

    @property
    def computed_risk_level(self) -> str:
        if self.score_overall is None:
            return "nd"
        if self.score_overall >= 75:
            return "verde"
        if self.score_overall >= 50:
            return "giallo"
        return "rosso"


class QuestionnaireTemplate(BaseModel):
    name = models.CharField(max_length=200)
    subject = models.CharField(max_length=300)
    body = models.TextField(
        help_text="Variabili: {supplier_name}, {questionnaire_link}"
    )
    form_url = models.URLField(max_length=500)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class SupplierQuestionnaire(BaseModel):
    RISK_CHOICES = [
        ("basso", "Basso"),
        ("medio", "Medio"),
        ("alto", "Alto"),
        ("critico", "Critico"),
    ]
    STATUS_CHOICES = [
        ("inviato", "In attesa"),
        ("risposto", "Risposto"),
        ("scaduto", "Scaduto"),
    ]
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name="questionnaires"
    )
    template = models.ForeignKey(
        QuestionnaireTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_questionnaires",
    )
    # Snapshot at send time
    subject_snapshot = models.CharField(max_length=300, blank=True)
    body_snapshot = models.TextField(blank=True)
    form_url_snapshot = models.URLField(max_length=500, blank=True)

    sent_at = models.DateTimeField()
    last_sent_at = models.DateTimeField()
    sent_to = models.EmailField()
    sent_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_questionnaires",
    )
    send_count = models.PositiveSmallIntegerField(default=1)

    evaluation_date = models.DateField(null=True, blank=True)
    risk_result = models.CharField(
        max_length=10, choices=RISK_CHOICES, null=True, blank=True
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="inviato"
    )
    expires_at = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-sent_at"]

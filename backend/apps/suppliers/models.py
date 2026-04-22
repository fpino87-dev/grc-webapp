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


class SupplierEvaluationConfig(models.Model):
    """
    Configurazione singleton per la valutazione interna fornitori.

    Mantiene pesi, label dei parametri, soglie di classificazione e parametri
    operativi (validità assessment esterno, bump NIS2). Tutto editabile via UI
    Impostazioni — nessun valore è hardcoded nel codice applicativo.
    """

    DEFAULT_WEIGHTS = {
        "impatto": 0.30,
        "accesso": 0.20,
        "dati": 0.20,
        "compliance": 0.15,
        "dipendenza": 0.10,
        "integrazione": 0.05,
    }

    DEFAULT_PARAMETER_LABELS = {
        "impatto": {
            "name": "Impatto business",
            "levels": ["Nessuno", "Minimo", "Degrado", "Interruzione", "Blocco"],
        },
        "accesso": {
            "name": "Accesso sistemi",
            "levels": ["Nessuno", "Limitato", "User", "Critico", "Admin"],
        },
        "dati": {
            "name": "Dati trattati",
            "levels": ["Pubblici", "Interni", "Sensibili", "Clienti", "Critici"],
        },
        "dipendenza": {
            "name": "Dipendenza fornitore",
            "levels": ["Facile", "Rapida", "Media", "Difficile", "Lock-in"],
        },
        "integrazione": {
            "name": "Integrazione IT",
            "levels": ["Nessuna", "Base", "API", "App", "Core"],
        },
        "compliance": {
            "name": "Compliance certificazioni cyber",
            "levels": [
                "TISAX L3 / ISO27001 + TISAX L2",
                "TISAX L2 / ISO27001",
                "ISO27001 in iter / SOC 2 / equivalenti",
                "Autocertificazione / policy interne",
                "Nessuna evidenza",
            ],
        },
    }

    DEFAULT_RISK_THRESHOLDS = {"medio": 2.0, "alto": 3.0, "critico": 4.0}

    weights = models.JSONField(
        default=dict,
        help_text="Pesi per ciascuno dei 6 parametri (somma = 1.00)",
    )
    parameter_labels = models.JSONField(
        default=dict,
        help_text="Nome parametro e label dei 5 livelli (1=basso rischio … 5=alto rischio)",
    )
    risk_thresholds = models.JSONField(
        default=dict,
        help_text="Soglie weighted_score per classificazione (>=)",
    )
    assessment_validity_months = models.PositiveSmallIntegerField(
        default=12,
        help_text="Mesi di validità di un assessment esterno approvato. Oltre, scade e non partecipa al risk_adj.",
    )
    nis2_concentration_bump = models.BooleanField(
        default=True,
        help_text="Se True, fornitori NIS2-rilevanti con concentrazione critica subiscono bump +1 classe sul risk_adj.",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        verbose_name = "Configurazione valutazione fornitori"
        verbose_name_plural = "Configurazione valutazione fornitori"

    def __str__(self):
        return "Configurazione valutazione fornitori (singleton)"

    @classmethod
    def get_solo(cls) -> "SupplierEvaluationConfig":
        """Ritorna l'unica istanza, creandola con i default se non esiste."""
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create(
                weights=cls.DEFAULT_WEIGHTS.copy(),
                parameter_labels={k: v.copy() for k, v in cls.DEFAULT_PARAMETER_LABELS.items()},
                risk_thresholds=cls.DEFAULT_RISK_THRESHOLDS.copy(),
            )
        return obj

    def classify(self, weighted_score: float) -> str:
        """Restituisce la classe di rischio (basso/medio/alto/critico) per un weighted_score."""
        thr = self.risk_thresholds or self.DEFAULT_RISK_THRESHOLDS
        if weighted_score >= float(thr.get("critico", 4.0)):
            return "critico"
        if weighted_score >= float(thr.get("alto", 3.0)):
            return "alto"
        if weighted_score >= float(thr.get("medio", 2.0)):
            return "medio"
        return "basso"


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

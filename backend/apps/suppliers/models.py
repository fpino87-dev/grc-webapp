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
    name = models.CharField(max_length=200)
    vat_number = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=2, default="IT")
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
    contract_expiry = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["name"]


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
    def risk_level(self):
        if self.score_overall is None:
            return "nd"
        if self.score_overall >= 75:
            return "verde"
        if self.score_overall >= 50:
            return "giallo"
        return "rosso"

from django.db import models
from django.contrib.auth import get_user_model
from core.models import BaseModel

User = get_user_model()


class ManagementReview(BaseModel):
    STATUS_CHOICES = [
        ("pianificato", "Pianificato"),
        ("in_corso", "In corso"),
        ("completato", "Completato"),
    ]
    plant = models.ForeignKey(
        "plants.Plant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="management_reviews",
    )
    title = models.CharField(max_length=200)
    review_date = models.DateField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="pianificato")
    chair = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chaired_reviews",
    )
    attendees = models.ManyToManyField(User, blank=True, related_name="attended_reviews")
    agenda = models.JSONField(default=list)
    kpi_snapshot = models.JSONField(default=dict)
    delibere = models.JSONField(default=list)
    next_review_date = models.DateField(null=True, blank=True)
    document_id = models.UUIDField(null=True, blank=True)

    # Snapshot dati al momento della creazione
    snapshot_generated_at = models.DateTimeField(null=True, blank=True)
    snapshot_data         = models.JSONField(default=dict)

    # Workflow approvazione
    approval_status = models.CharField(
        max_length=20,
        choices=[
            ("bozza",      "Bozza"),
            ("in_review",  "In revisione"),
            ("approvato",  "Approvato"),
            ("rifiutato",  "Rifiutato"),
        ],
        default="bozza",
    )
    approved_by   = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_reviews",
    )
    approved_at   = models.DateTimeField(null=True, blank=True)
    approval_note = models.TextField(blank=True)

    # Sintesi executive del verbale. Può essere scritta a mano o partire da una
    # bozza IA (M20): la bozza resta separata finché un utente non la accetta
    # (human-in-the-loop), e i metadati dicono se e come l'IA ha contribuito.
    executive_summary = models.TextField(blank=True)
    executive_summary_meta = models.JSONField(default=dict, blank=True)
    executive_summary_draft = models.TextField(blank=True)
    executive_summary_draft_meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-review_date"]


class ReviewAgendaItem(BaseModel):
    """Punto dell'ordine del giorno. I punti obbligatori ISO 27001 §9.3.2 sono
    creati con il riesame (`code` ≠ "custom"); altri si aggiungono a mano."""

    review = models.ForeignKey(
        ManagementReview, on_delete=models.CASCADE, related_name="agenda_items"
    )
    code = models.CharField(max_length=30, default="custom")
    title = models.CharField(max_length=200, blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    mandatory = models.BooleanField(default=False)
    discussion = models.TextField(blank=True)

    class Meta:
        ordering = ["order", "created_at"]


class ReviewAction(BaseModel):
    STATUS_CHOICES = [("aperto", "Aperto"), ("chiuso", "Chiuso")]
    # Output del riesame (ISO 27001 §9.3.3)
    DECISION_TYPE_CHOICES = [
        ("miglioramento", "Opportunità di miglioramento"),
        ("modifica_sgsi", "Modifica al SGSI"),
        ("risorse", "Risorse"),
        # La direzione può uscire dal riesame con un obiettivo di sicurezza
        # nuovo o rivisto: è il passaggio §9.3.3 (output) → §6.2 (obiettivi).
        ("obiettivo", "Obiettivo di sicurezza"),
        ("altro", "Altro"),
    ]
    review = models.ForeignKey(
        ManagementReview, on_delete=models.CASCADE, related_name="actions"
    )
    agenda_item = models.ForeignKey(
        ReviewAgendaItem, on_delete=models.SET_NULL, null=True, blank=True, related_name="decisions"
    )
    decision_type = models.CharField(max_length=20, choices=DECISION_TYPE_CHOICES, default="miglioramento")
    task = models.ForeignKey(
        "tasks.Task", on_delete=models.SET_NULL, null=True, blank=True, related_name="review_actions"
    )
    pdca_cycle = models.ForeignKey(
        "pdca.PdcaCycle", on_delete=models.SET_NULL, null=True, blank=True, related_name="review_actions"
    )
    security_objective = models.ForeignKey(
        "governance.SecurityObjective", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="review_actions",
    )
    description = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="aperto")
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["due_date", "created_at"]

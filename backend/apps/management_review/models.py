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

    class Meta:
        ordering = ["-review_date"]


class ReviewAction(BaseModel):
    STATUS_CHOICES = [("aperto", "Aperto"), ("chiuso", "Chiuso")]
    review = models.ForeignKey(
        ManagementReview, on_delete=models.CASCADE, related_name="actions"
    )
    description = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="aperto")
    closed_at = models.DateTimeField(null=True, blank=True)

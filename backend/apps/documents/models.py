import hashlib
from django.db import models
from django.contrib.auth import get_user_model
from core.models import BaseModel

User = get_user_model()


class Document(BaseModel):
    CATEGORY_CHOICES = [
        ("politica", "Politica"),
        ("procedura", "Procedura"),
        ("istruzione", "Istruzione operativa"),
        ("registro", "Registro"),
        ("evidence", "Evidence"),
        ("verbale", "Verbale"),
        ("contratto", "Contratto"),
        ("altro", "Altro"),
    ]
    STATUS_CHOICES = [
        ("bozza", "Bozza"),
        ("revisione", "In revisione"),
        ("approvazione", "In approvazione"),
        ("approvato", "Approvato"),
        ("archiviato", "Archiviato"),
    ]

    title = models.CharField(max_length=300)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="bozza")
    plant = models.ForeignKey(
        "plants.Plant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="documents",
    )
    framework_refs = models.JSONField(default=list)
    control_refs = models.ManyToManyField(
        "controls.ControlInstance",
        blank=True,
        related_name="documents",
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_documents",
    )
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="review_documents",
    )
    approver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approval_documents",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    review_due_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    is_mandatory = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class DocumentVersion(BaseModel):
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    version_number = models.PositiveIntegerField()
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(null=True, blank=True)
    sha256 = models.CharField(max_length=64)
    storage_path = models.CharField(max_length=500)
    change_summary = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        unique_together = [["document", "version_number"]]
        ordering = ["-version_number"]


class DocumentApproval(BaseModel):
    ACTION_CHOICES = [
        ("approve", "Approvato"),
        ("reject", "Rifiutato"),
        ("request_changes", "Modifiche richieste"),
    ]

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="approvals",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)

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

    DOCUMENT_TYPE_CHOICES = [
        ("policy", "Policy"),
        ("procedura", "Procedura"),
        ("manuale", "Manuale ISMS"),
        ("contratto", "Contratto/NDA"),
        ("registro", "Registro"),
        ("altro", "Altro"),
    ]

    title = models.CharField(max_length=300)
    document_code = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        help_text="Codice identificativo del documento (es. D-ITA-INF-001). Libero, unico per convenzione aziendale.",
    )
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, db_index=True)
    document_type = models.CharField(
        max_length=20,
        choices=DOCUMENT_TYPE_CHOICES,
        default="policy",
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="bozza",
        db_index=True,
    )
    plant = models.ForeignKey(
        "plants.Plant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="documents",
        db_index=True,
    )
    shared_plants = models.ManyToManyField(
        "plants.Plant",
        blank=True,
        related_name="shared_documents",
        help_text="Plant aggiuntivi che possono vedere questo documento senza essere il proprietario",
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
    review_due_date = models.DateField(null=True, blank=True, db_index=True)
    expiry_date = models.DateField(null=True, blank=True)
    is_mandatory = models.BooleanField(default=False)
    supplier = models.ForeignKey(
        "suppliers.Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nda_documents",
    )

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


class Evidence(BaseModel):
    EVIDENCE_TYPE_CHOICES = [
        ("screenshot", "Screenshot"),
        ("log", "Log di sistema"),
        ("report", "Report"),
        ("verbale", "Verbale"),
        ("certificato", "Certificato"),
        ("test_result", "Risultato test"),
        ("altro", "Altro"),
    ]

    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    evidence_type = models.CharField(max_length=20, choices=EVIDENCE_TYPE_CHOICES, default="altro")
    valid_until = models.DateField(null=True, blank=True, db_index=True)
    plant = models.ForeignKey(
        "plants.Plant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evidences",
    )
    file_path = models.CharField(max_length=500, blank=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_evidences",
    )

    class Meta:
        ordering = ["valid_until"]

    def __str__(self):
        return self.title

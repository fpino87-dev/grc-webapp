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
    # Organo che tiene e approva il riesame (CdA, comitato, direzione): da qui
    # si propongono i partecipanti. Facoltativo: un riesame può essere tenuto
    # dalla direzione senza un organo formalizzato in anagrafica.
    governing_body = models.ForeignKey(
        "governance.SecurityCommittee",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="management_reviews",
    )
    # Logo in testa al verbale PDF/HTML: quello di uno dei siti (società) già
    # caricato in Plant Registry. È presentazione, non contenuto: resta
    # modificabile anche dopo l'approvazione (con audit).
    report_logo_plant = models.ForeignKey(
        "plants.Plant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
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
    # Due forme di approvazione (§9.3): in app, da chi preme il pulsante —
    # un componente dell'organo con account, o governance che registra; oppure
    # con delibera dell'organo, di cui si riportano estremi ed evidenza (M07).
    # `approved_by` resta in entrambi i casi chi ha registrato l'approvazione.
    APPROVAL_MODE_CHOICES = [
        ("in_app", "In applicazione"),
        ("delibera", "Delibera dell'organo"),
    ]
    approval_mode = models.CharField(max_length=10, choices=APPROVAL_MODE_CHOICES, blank=True)
    approved_member = models.ForeignKey(
        "governance.CommitteeMember",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_reviews",
    )
    approval_resolution_ref = models.CharField(max_length=100, blank=True)
    approval_resolution_date = models.DateField(null=True, blank=True)
    approval_document_id = models.UUIDField(null=True, blank=True)

    # Sintesi executive del verbale. Può essere scritta a mano o partire da una
    # bozza IA (M20): la bozza resta separata finché un utente non la accetta
    # (human-in-the-loop), e i metadati dicono se e come l'IA ha contribuito.
    executive_summary = models.TextField(blank=True)
    executive_summary_meta = models.JSONField(default=dict, blank=True)
    executive_summary_draft = models.TextField(blank=True)
    executive_summary_draft_meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-review_date"]


class ReviewParticipant(BaseModel):
    """Chi era convocato al riesame e con quale esito di presenza.

    Nome e qualifica sono **congelati** alla data del riesame: il verbale deve
    restare quello che era anche se il componente lascia la carica o cambia
    qualifica. `member` e `user` sono il collegamento all'anagrafica (entrambi
    facoltativi: un ospite occasionale non è in nessuna delle due).
    """

    ROLE_CHOICES = [
        ("presidente", "Presidente"),
        ("membro", "Membro"),
        ("segretario", "Segretario"),
        ("ospite", "Ospite"),
    ]
    ATTENDANCE_CHOICES = [
        ("presente", "Presente"),
        ("assente", "Assente"),
        ("delegato", "Rappresentato da delegato"),
    ]

    review = models.ForeignKey(
        ManagementReview, on_delete=models.CASCADE, related_name="participants"
    )
    member = models.ForeignKey(
        "governance.CommitteeMember",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="review_participations",
    )
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="review_participations"
    )
    full_name = models.CharField(max_length=200)
    position = models.CharField(max_length=200, blank=True)
    body_role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="membro")
    is_chair = models.BooleanField(default=False)
    attendance = models.CharField(max_length=10, choices=ATTENDANCE_CHOICES, default="presente")
    delegate_name = models.CharField(max_length=200, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self):
        return f"{self.full_name} @ {self.review_id}"


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

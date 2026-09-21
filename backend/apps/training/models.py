from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel

User = get_user_model()


class TrainingCourse(BaseModel):
    """Corso o campagna del catalogo formativo.

    La piattaforma non eroga la formazione: il corso descrive cosa va fatto,
    per chi, ogni quanto va ripetuto (`validity_months`) e in quale ambito
    (organizzazione o siti). I controlli che le erogazioni provano dipendono
    dai destinatari (`TrainingEvidenceControl`), non dal singolo corso.
    """

    SOURCE_CHOICES = [("interno", "Interno"), ("kb4", "KnowBe4"), ("esterno", "Esterno")]
    STATUS_CHOICES = [("attivo", "Attivo"), ("archiviato", "Archiviato")]
    KIND_CHOICES = [
        ("corso", _("Corso")),
        ("awareness", _("Campagna di sensibilizzazione")),
        ("phishing", _("Simulazione di phishing")),
    ]
    AUDIENCE_KIND_CHOICES = [
        ("generale", _("Personale")),
        ("ruoli_critici", _("Ruoli critici")),
        ("organo_gestione", _("Organo di gestione")),
    ]

    title = models.CharField(max_length=300)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="interno")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="attivo")
    kb4_campaign_id = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    duration_minutes = models.IntegerField(null=True, blank=True)
    mandatory = models.BooleanField(default=False)
    # Deprecato: sostituito da `controls` (a sua volta deprecato), da eliminare.
    framework_refs = models.JSONField(default=list)
    # Ambito: nessun sito = corso di organizzazione, valido per tutti i siti
    # (es. igiene standard); uno o più siti = corso specifico di quei siti.
    plants = models.ManyToManyField("plants.Plant", blank=True, related_name="training_courses")
    deadline = models.DateField(null=True, blank=True)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default="corso")
    audience_kind = models.CharField(
        max_length=20, choices=AUDIENCE_KIND_CHOICES, default="generale",
    )
    # Mesi di validità di un'erogazione: dopo va ripetuta. Null = non scade.
    validity_months = models.PositiveSmallIntegerField(null=True, blank=True, default=12)
    # Deprecato: i controlli provati dalle erogazioni si impostano per tipo di
    # destinatari (TrainingEvidenceControl). Copiato dalla migrazione 0006,
    # eliminato nella release successiva insieme a framework_refs.
    controls = models.ManyToManyField(
        "controls.Control", blank=True, related_name="training_courses",
    )
    # Ruoli critici e organo di gestione: la competenza (ISO 27001 cl. 7.2) che
    # l'erogazione attribuisce ai partecipanti con account, e a quale livello.
    competency = models.CharField(max_length=200, blank=True)
    competency_level = models.PositiveSmallIntegerField(
        choices=[(1, "1"), (2, "2"), (3, "3")], default=1,
    )

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_named(self) -> bool:
        """Le erogazioni di questo corso elencano i partecipanti per nome
        (titolari di nomine, componenti degli organi di governo)."""
        return self.audience_kind != "generale" and self.kind != "phishing"


class TrainingEvidenceControl(BaseModel):
    """Impostazione unica del modulo: quali controlli prova un'erogazione, in
    base ai destinatari del corso (es. personale → ACN PR.AT-01, ISO A.6.3).
    La prova si collega solo ai controlli istanziati sul sito dell'erogazione,
    quindi solo dove il framework è applicato. I framework non si toccano."""

    audience_kind = models.CharField(
        max_length=20, choices=TrainingCourse.AUDIENCE_KIND_CHOICES,
    )
    control = models.ForeignKey(
        "controls.Control", on_delete=models.CASCADE, related_name="training_evidence_rules",
    )

    class Meta:
        ordering = ["audience_kind", "control__external_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["audience_kind", "control"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_training_evidence_control",
            ),
        ]


class TrainingAudience(BaseModel):
    """Gruppo di destinatari di un sito, contato e non nominativo
    (es. «Produzione»: 240 persone). Nessun dato personale dei dipendenti."""

    plant = models.ForeignKey(
        "plants.Plant", on_delete=models.PROTECT, related_name="training_audiences",
    )
    name = models.CharField(max_length=150)
    headcount = models.PositiveIntegerField()
    headcount_updated_at = models.DateField()
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["plant", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["plant", "name"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_training_audience_plant_name",
            ),
        ]


class TrainingPlan(BaseModel):
    """Piano formativo annuale di un sito (o di organizzazione se `plant` è
    null). L'approvazione passa dal documento M07 collegato: il piano approvato
    è il documento richiesto da ISO 27001 A.6.3."""

    plant = models.ForeignKey(
        "plants.Plant", on_delete=models.PROTECT, null=True, blank=True,
        related_name="training_plans",
    )
    year = models.PositiveSmallIntegerField()
    document = models.ForeignKey(
        "documents.Document", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="training_plans",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-year"]
        constraints = [
            models.UniqueConstraint(
                fields=["plant", "year"],
                condition=Q(deleted_at__isnull=True),
                nulls_distinct=False,
                name="uniq_training_plan_plant_year",
            ),
        ]


class TrainingPlanItem(BaseModel):
    """Voce del piano: quale corso, per quali gruppi, entro quando."""

    plan = models.ForeignKey(TrainingPlan, on_delete=models.CASCADE, related_name="items")
    course = models.ForeignKey(
        TrainingCourse, on_delete=models.PROTECT, related_name="plan_items",
    )
    audiences = models.ManyToManyField(TrainingAudience, blank=True, related_name="plan_items")
    due_date = models.DateField(db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["due_date"]


class TrainingSession(BaseModel):
    """Erogazione registrata: conteggi più il file di prova allegato
    (registro presenze, export e-learning, report della campagna), da cui
    nasce l'evidenza. Le righe `legacy` vengono dalla migrazione dei vecchi
    dati per persona e non hanno evidenza."""

    course = models.ForeignKey(
        TrainingCourse, on_delete=models.PROTECT, related_name="sessions",
    )
    plan_item = models.ForeignKey(
        TrainingPlanItem, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sessions",
    )
    plant = models.ForeignKey(
        "plants.Plant", on_delete=models.PROTECT, null=True, blank=True,
        related_name="training_sessions",
    )
    held_on = models.DateField(db_index=True)
    audiences = models.ManyToManyField(TrainingAudience, blank=True, related_name="sessions")
    # Corsi e campagne di sensibilizzazione
    target_count = models.PositiveIntegerField(null=True, blank=True)
    trained_count = models.PositiveIntegerField(null=True, blank=True)
    # Simulazioni di phishing
    sent_count = models.PositiveIntegerField(null=True, blank=True)
    clicked_count = models.PositiveIntegerField(null=True, blank=True)
    reported_count = models.PositiveIntegerField(null=True, blank=True)
    evidence = models.ForeignKey(
        "documents.Evidence", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="training_sessions",
    )
    legacy = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-held_on"]


class TrainingParticipant(BaseModel):
    """Partecipante nominativo di un'erogazione per ruoli critici o per l'organo
    di gestione: titolare di una nomina (M00) o componente di un organo di
    governo, anche senza account. Il personale generale resta solo contato.

    `competency` è la `UserCompetency` aggiornata dall'erogazione (solo per chi
    ha un account); `competency_before` ne conserva lo stato precedente, per
    ripristinarlo se l'erogazione viene eliminata (null = creata da questa)."""

    session = models.ForeignKey(
        TrainingSession, on_delete=models.CASCADE, related_name="participants",
    )
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="training_participations",
    )
    committee_member = models.ForeignKey(
        "governance.CommitteeMember", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="training_participations",
    )
    # Nomine attive sul sito alla data dell'erogazione (fotografia, per la prova).
    roles = models.JSONField(default=list, blank=True)
    competency = models.ForeignKey(
        "auth_grc.UserCompetency", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="training_participations",
    )
    competency_before = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]


class TrainingEnrollment(BaseModel):
    STATUS_CHOICES = [
        ("assegnato", "Assegnato"),
        ("in_corso", "In corso"),
        ("completato", "Completato"),
        ("scaduto", "Scaduto"),
    ]

    course = models.ForeignKey(TrainingCourse, on_delete=models.CASCADE, related_name="enrollments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="training_enrollments")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="assegnato")
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.IntegerField(null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)

    class Meta:
        unique_together = [["course", "user"]]
        ordering = ["-created_at"]


class PhishingSimulation(BaseModel):
    RESULT_CHOICES = [
        ("clicked", "Clicked"),
        ("reported", "Reported"),
        ("ignored", "Ignored"),
    ]

    kb4_simulation_id = models.CharField(max_length=100, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="phishing_results")
    plant = models.ForeignKey("plants.Plant", on_delete=models.PROTECT, null=True, blank=True)
    result = models.CharField(max_length=15, choices=RESULT_CHOICES)
    sent_at = models.DateTimeField()
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-sent_at"]

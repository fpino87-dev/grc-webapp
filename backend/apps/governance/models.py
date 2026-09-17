from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField

from core.models import BaseModel


class NormativeRole(models.TextChoices):
    CISO = "ciso", _("CISO")
    COMPLIANCE_OFFICER = "compliance_officer", _("Compliance Officer")
    RISK_MANAGER = "risk_manager", _("Risk Manager")
    INTERNAL_AUDITOR = "internal_auditor", _("Auditor Interno")
    EXTERNAL_AUDITOR = "external_auditor", _("Auditor Esterno")
    PLANT_MANAGER = "plant_manager", _("Plant Manager")
    CONTROL_OWNER = "control_owner", _("Control Owner")
    PLANT_SECURITY_OFFICER = "plant_security_officer", _("Plant Security Officer")
    NIS2_CONTACT = "nis2_contact", _("Contatto NIS2")
    DPO = "dpo", _("DPO")
    ISMS_MANAGER = "isms_manager", _("ISMS Manager")
    COMITATO_MEMBRO = "comitato_membro", _("Membro Comitato")
    BU_REFERENTE = "bu_referente", _("Referente BU")
    RACI_RESPONSIBLE = "raci_responsible", _("RACI Responsible")
    RACI_ACCOUNTABLE = "raci_accountable", _("RACI Accountable")


class RoleAssignment(BaseModel):
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )
    role = models.CharField(max_length=50, choices=NormativeRole.choices)
    scope_type = models.CharField(
        max_length=20,
        choices=[("org", "Org"), ("bu", "BU"), ("plant", "Plant")],
    )
    scope_id = models.UUIDField(null=True, blank=True)
    valid_from = models.DateField()
    valid_until = models.DateField(null=True, blank=True)
    signed_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="signed_assignments",
    )
    document_id = models.UUIDField(null=True, blank=True)
    framework_refs = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-valid_from", "role"]
        constraints = [
            # Stesso utente, stesso ruolo, stesso perimetro, due nomine aperte:
            # non esiste un caso legittimo (una rinomina passa da Termina o
            # Sostituisci, che chiudono la precedente). nulls_distinct=False
            # copre anche le nomine org, dove scope_id è NULL. Il titolare
            # unico fra utenti diversi dipende da RoleRequirement e resta
            # controllato in services.create_role_assignment.
            models.UniqueConstraint(
                fields=["user", "role", "scope_type", "scope_id"],
                condition=models.Q(deleted_at__isnull=True, valid_until__isnull=True),
                nulls_distinct=False,
                name="uniq_open_role_assignment",
            ),
        ]

    @property
    def is_active(self):
        from django.utils import timezone

        today = timezone.localdate()
        return self.valid_from <= today and (
            self.valid_until is None or self.valid_until >= today
        )


class DocumentWorkflowPolicy(BaseModel):
    """
    Policy di governance per il workflow documentale M07.

    Definisce, per tipo documento e per scope (org / BU / plant),
    quali ruoli NORMATIVI possono:
    - creare / inviare in revisione
    - revisionare
    - approvare il documento.
    """

    SCOPE_CHOICES = [
        ("org", "Org"),
        ("bu", "BU"),
        ("plant", "Plant"),
    ]

    document_type = models.CharField(
        max_length=20,
        help_text="Tipo documento M07 (es. policy, procedura, manuale, contratto, registro, altro).",
    )
    scope_type = models.CharField(max_length=10, choices=SCOPE_CHOICES, default="org")
    scope_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Per scope_type=bu/plant contiene l'UUID della BU o del Plant.",
    )
    submit_roles = ArrayField(
        models.CharField(max_length=50, choices=NormativeRole.choices),
        default=list,
        blank=True,
        help_text="Ruoli che possono creare/inviare in revisione documenti di questo tipo nello scope indicato.",
    )
    review_roles = ArrayField(
        models.CharField(max_length=50, choices=NormativeRole.choices),
        default=list,
        blank=True,
        help_text="Ruoli che possono svolgere la revisione.",
    )
    approve_roles = ArrayField(
        models.CharField(max_length=50, choices=NormativeRole.choices),
        default=list,
        blank=True,
        help_text="Ruoli che possono approvare/mandare in vigore il documento.",
    )

    class Meta:
        verbose_name = "Document workflow policy"
        verbose_name_plural = "Document workflow policies"
        ordering = ["document_type", "scope_type"]


class SecurityCommittee(BaseModel):
    plant = models.ForeignKey(
        "plants.Plant",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    name = models.CharField(max_length=200)
    committee_type = models.CharField(
        max_length=20,
        choices=[("centrale", "Centrale"), ("bu", "BU")],
    )
    frequency = models.CharField(
        max_length=20,
        choices=[
            ("mensile", "Mensile"),
            ("trimestrale", "Trimestrale"),
            ("semestrale", "Semestrale"),
        ],
    )
    next_meeting_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]


class CommitteeMeeting(BaseModel):
    committee = models.ForeignKey(
        SecurityCommittee,
        on_delete=models.CASCADE,
        related_name="meetings",
    )
    held_at = models.DateTimeField()
    verbale_doc_id = models.UUIDField(null=True, blank=True)
    delibere = models.JSONField(default=list)
    attendees = models.ManyToManyField("auth.User", blank=True)

    class Meta:
        ordering = ["-held_at"]


class RoleRequirement(BaseModel):
    """
    Definisce QUALI ruoli normativi sono obbligatori e a QUALE scope, alimentando
    la matrice di copertura (M00) e ``get_vacant_mandatory_roles``.

    Tre profili di copertura:
    - ``scope_level="org"``: un solo titolare org copre l'azienda (es. CISO).
    - ``scope_level="plant"`` + ``org_covers_sites=False``: va nominato per ogni
      sito in perimetro, un'assegnazione org NON copre (es. NIS2 Contact).
    - ``scope_level="plant"`` + ``org_covers_sites=True``: un titolare org copre
      i siti privi di nomina specifica, ma il sito può nominare il proprio
      titolare che ha la precedenza (es. DPO — può variare per entità giuridica).

    L'elenco è configurabile dagli admin (CRUD da UI); i default sono caricati da
    ``load_role_requirements``.
    """

    SCOPE_LEVEL_CHOICES = [
        ("org", "Org"),
        ("plant", "Plant"),
    ]
    APPLIES_TO_CHOICES = [
        ("all", "Tutti i siti"),
        ("nis2_only", "Solo siti NIS2"),
    ]

    role = models.CharField(max_length=50, choices=NormativeRole.choices)
    scope_level = models.CharField(max_length=10, choices=SCOPE_LEVEL_CHOICES, default="org")
    applies_to = models.CharField(
        max_length=20,
        choices=APPLIES_TO_CHOICES,
        default="all",
        help_text="Usato solo per scope_level=plant: a quali siti si applica il requisito.",
    )
    org_covers_sites = models.BooleanField(
        default=False,
        help_text=(
            "Solo per scope_level=plant: se True un'assegnazione org attiva copre "
            "i siti privi di nomina specifica (caso DPO); se False ogni sito va "
            "nominato (caso NIS2 Contact)."
        ),
    )
    mandatory = models.BooleanField(
        default=True,
        help_text=(
            "Se True il ruolo è obbligatorio: la matrice segnala come lacuna i "
            "perimetri scoperti. Se False la riga serve solo a definire la "
            "policy del ruolo (es. titolare unico) senza imporne la copertura."
        ),
    )
    single_holder = models.BooleanField(
        default=True,
        help_text=(
            "Se True il ruolo ammette un solo titolare attivo per perimetro "
            "(la seconda assegnazione è bloccata: usare Sostituisci). Se False "
            "sono ammessi più titolari (es. Control Owner, membri comitato)."
        ),
    )
    enabled = models.BooleanField(
        default=True,
        help_text="Disattiva il requisito senza eliminarlo (escluso dalla matrice).",
    )
    framework_refs = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
        help_text="Riferimenti normativi per evidenza audit (es. ISO27001:A.5.2).",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["scope_level", "role"]
        constraints = [
            models.UniqueConstraint(
                fields=["role", "scope_level"],
                condition=models.Q(deleted_at__isnull=True),
                name="uniq_active_role_requirement",
            ),
        ]

    def __str__(self):
        return f"{self.role} @ {self.scope_level}"



class SecurityObjective(BaseModel):
    """Obiettivo di sicurezza delle informazioni (ISO/IEC 27001:2022 §6.2).

    Un obiettivo NON è un KPI, ed è la ragione per cui esiste questo modello
    invece di un flag su `KPIDefinition`:

      * il KPI risponde a "a che punto siamo adesso?" e le sue soglie sono un
        *pavimento* tarato sul rischio — sotto quel livello si interviene
        subito, e la soglia non va allargata per fare spazio a un'ambizione;
      * l'obiettivo risponde a "arriveremo dove ci siamo impegnati, entro la
        data promessa?" ed è una *traiettoria* verso un target, con un ruolo
        che ne risponde.

    Lo stesso numero può essere verde sulla soglia e rosso sull'obiettivo (in
    linea oggi, fermo da mesi rispetto al target di dicembre) e viceversa (un
    calo isolato che fa scattare l'alert ma non intacca la traiettoria).

    Per questo l'obiettivo non ha soglie proprie né un proprio calcolo: se è
    agganciato a un KPI (`measure_source="kpi"`) legge i valori dagli snapshot
    settimanali del motore M08 — una sola misura, una sola verità sul numero.
    Le misure manuali (`SecurityObjectiveMeasurement`) servono solo a ciò che
    la piattaforma non misura da sé.

    Solo pochi KPI meritano un obiettivo (tipicamente 4-6 all'anno): quelli
    dove esiste un divario da colmare. Dove il processo già funziona basta
    sorvegliarlo con le soglie.
    """

    STATUS_CHOICES = [
        ("bozza", "Bozza"),
        ("attivo", "Attivo"),
        ("raggiunto", "Raggiunto"),
        ("non_raggiunto", "Non raggiunto"),
        ("sospeso", "Sospeso"),
        ("annullato", "Annullato"),
    ]
    # §6.2 chiede di tenere conto dei requisiti di sicurezza applicabili e dei
    # risultati della valutazione del rischio: l'origine rende tracciabile da
    # dove nasce l'impegno.
    ORIGIN_CHOICES = [
        ("politica", "Politica di sicurezza"),
        ("risk_assessment", "Valutazione del rischio"),
        ("audit", "Esito di audit"),
        ("requisito", "Requisito normativo o contrattuale"),
        ("incidente", "Incidente"),
        ("riesame", "Riesame di direzione"),
        ("altro", "Altro"),
    ]
    MEASURE_SOURCE_CHOICES = [
        ("kpi", "KPI operativo (M08)"),
        ("manual", "Misura manuale"),
    ]
    # Stessa semantica di KPIDefinition.threshold_direction, e per lo stesso
    # motivo: "above" = valore alto è buono.
    DIRECTION_CHOICES = [
        ("above", "Sopra il target = raggiunto"),
        ("below", "Sotto il target = raggiunto"),
    ]

    plant = models.ForeignKey(
        "plants.Plant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="security_objectives",
        db_index=True,
        help_text=(
            "Sito a cui si riferisce l'obiettivo. null = obiettivo di "
            "organizzazione, valido per tutti i siti."
        ),
    )
    code = models.CharField(max_length=30, db_index=True, help_text="Es: OBJ-2026-01")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    origin = models.CharField(max_length=20, choices=ORIGIN_CHOICES, default="politica")
    # Riesame di direzione che ha deliberato l'obiettivo. UUID e non FK per
    # non accoppiare le migrazioni di governance a quelle di M13 (stesso
    # criterio di RoleAssignment.document_id).
    source_review_id = models.UUIDField(null=True, blank=True)

    # ── Misura ────────────────────────────────────────────────────────────
    measure_source = models.CharField(
        max_length=10, choices=MEASURE_SOURCE_CHOICES, default="kpi"
    )
    kpi_definition = models.ForeignKey(
        "tasks.KPIDefinition",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="security_objectives",
        help_text="KPI da cui leggere i valori se measure_source=kpi.",
    )
    unit = models.CharField(
        max_length=20,
        blank=True,
        help_text="Unità delle misure manuali; con un KPI si usa quella del KPI.",
    )

    # ── Traiettoria ───────────────────────────────────────────────────────
    start_date = models.DateField(help_text="Inizio del periodo di impegno.")
    baseline_value = models.FloatField(
        null=True, blank=True, help_text="Valore di partenza, da cui si misura il progresso."
    )
    target_value = models.FloatField()
    target_direction = models.CharField(
        max_length=5, choices=DIRECTION_CHOICES, default="above"
    )
    target_date = models.DateField(db_index=True)

    # ── Piano (§6.2 e-f: chi, con quali risorse, come si valuta) ──────────
    # Ruolo e non utente: il responsabile si risolve dinamicamente via
    # UserPlantAccess, come per i task M08 (regola architetturale #7).
    owner_role = models.CharField(
        max_length=50,
        blank=True,
        help_text="Ruolo GRC che risponde dell'obiettivo (risolto via UserPlantAccess).",
    )
    resources = models.TextField(blank=True, help_text="Risorse necessarie (§6.2 e).")
    evaluation_method = models.TextField(
        blank=True, help_text="Come si valuta il risultato (§6.2 f)."
    )

    # ── Ciclo di vita ─────────────────────────────────────────────────────
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default="bozza", db_index=True
    )
    # §6.2: l'obiettivo deve essere comunicato. Il documento pubblicato (M07)
    # è l'evidenza; l'id resta UUID per lo stesso motivo di source_review_id.
    communicated_at = models.DateTimeField(null=True, blank=True)
    document_id = models.UUIDField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="closed_security_objectives",
    )
    closure_note = models.TextField(blank=True)

    # ── Memoria della sorveglianza automatica ─────────────────────────────
    # Si notifica quando la traiettoria PEGGIORA, non a ogni giro: senza
    # ricordare l'ultima lettura, l'obiettivo in ritardo manderebbe la stessa
    # email ogni settimana fino alla scadenza, e la si imparerebbe a ignorare
    # (stesso criterio degli alert KPI, `_kpi_status_worsened`).
    last_track = models.CharField(max_length=20, blank=True)
    last_evaluated_at = models.DateTimeField(null=True, blank=True)
    # Promemoria di avvicinamento alla scadenza: una volta sola.
    deadline_notice_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["target_date", "code"]
        indexes = [
            models.Index(fields=["status", "target_date"]),
        ]
        constraints = [
            # Stesso schema di KPIDefinition: in Postgres NULL != NULL, quindi
            # un solo indice unico su (code, plant) lascerebbe passare due
            # obiettivi di organizzazione con lo stesso codice. La condizione
            # su deleted_at libera il codice dopo una cancellazione logica.
            models.UniqueConstraint(
                fields=["code", "plant"],
                condition=models.Q(deleted_at__isnull=True, plant__isnull=False),
                name="uniq_active_objective_code_per_plant",
            ),
            models.UniqueConstraint(
                fields=["code"],
                condition=models.Q(deleted_at__isnull=True, plant__isnull=True),
                name="uniq_active_objective_code_global",
            ),
        ]

    def __str__(self):
        return f"{self.code} — {self.title}"


class SecurityObjectiveMeasurement(BaseModel):
    """Misura manuale di un obiettivo (§6.2: gli obiettivi vanno monitorati).

    Esiste solo per gli obiettivi `measure_source="manual"`: quando l'obiettivo
    è agganciato a un KPI le misure sono già gli `OperationalKpiSnapshot`
    settimanali e duplicarle qui creerebbe due verità sullo stesso numero.
    """

    objective = models.ForeignKey(
        SecurityObjective, on_delete=models.CASCADE, related_name="measurements"
    )
    measured_on = models.DateField(db_index=True)
    value = models.FloatField()
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-measured_on"]
        constraints = [
            models.UniqueConstraint(
                fields=["objective", "measured_on"],
                condition=models.Q(deleted_at__isnull=True),
                name="uniq_active_objective_measurement_per_day",
            ),
        ]

    def __str__(self):
        return f"{self.objective_id} @ {self.measured_on}: {self.value}"

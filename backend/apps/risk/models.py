from django.db import models

from core.models import BaseModel


NIS2_ART21_CHOICES = [
    ("art21_a", "Art.21(2)(a) – Analisi dei rischi e policy ISMS"),
    ("art21_b", "Art.21(2)(b) – Gestione incidenti"),
    ("art21_c", "Art.21(2)(c) – Continuità operativa e BCP/DR"),
    ("art21_d", "Art.21(2)(d) – Supply chain"),
    ("art21_e", "Art.21(2)(e) – Sicurezza acquisizione e manutenzione sistemi"),
    ("art21_f", "Art.21(2)(f) – Verifica efficacia delle misure di sicurezza"),
    ("art21_g", "Art.21(2)(g) – Igiene informatica e formazione"),
    ("art21_h", "Art.21(2)(h) – Crittografia e protezione dati"),
    ("art21_i", "Art.21(2)(i) – Controllo accessi, IAM e gestione asset"),
    ("art21_j", "Art.21(2)(j) – MFA e comunicazioni sicure"),
]

PROB_CHOICES = [(1,"1 – Molto bassa"),(2,"2 – Bassa"),(3,"3 – Media"),(4,"4 – Alta"),(5,"5 – Molto alta")]
IMPACT_CHOICES = [(1,"1 – Trascurabile"),(2,"2 – Minore"),(3,"3 – Moderato"),(4,"4 – Grave"),(5,"5 – Critico")]
TREATMENT_CHOICES = [("mitigare","Mitigare"),("accettare","Accettare"),("trasferire","Trasferire"),("evitare","Evitare")]


class RiskAssessment(BaseModel):
    # Nullo = rischio del registro di gruppo (procedura §4.3), ereditato dai
    # siti in `affected_plants`.
    plant = models.ForeignKey("plants.Plant", null=True, blank=True, on_delete=models.CASCADE)
    asset = models.ForeignKey(
        "assets.Asset",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="risk_assessments",
    )
    name = models.CharField(max_length=200, blank=True, default="")
    # Rischio attuale: probabilità e impatto complessivo (caso peggiore delle
    # dimensioni, calcolato da risk.services.recompute_risk).
    probability = models.IntegerField(null=True, blank=True, choices=PROB_CHOICES)
    impact = models.IntegerField(null=True, blank=True, choices=IMPACT_CHOICES)
    treatment = models.CharField(max_length=20, blank=True, default="", choices=TREATMENT_CHOICES)
    status = models.CharField(
        max_length=20,
        choices=[("bozza", "Bozza"), ("completato", "Completato"), ("archiviato", "Archiviato")],
        default="bozza",
        db_index=True,
    )
    assessed_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    owner = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_risks",
        help_text="Responsabile del rischio (diverso da chi lo ha valutato)",
    )
    # Responsabile del trattamento: chi realizza le misure (spesso IT/OT), distinto
    # dal risk owner che ne risponde. Campo misto: utente del portale OPPURE testo
    # libero (es. fornitore esterno/MSP); se c'è l'utente il testo resta vuoto.
    treatment_owner = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="treated_risks",
        help_text="Responsabile del trattamento (utente del portale)",
    )
    treatment_owner_external = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Responsabile del trattamento non utente del portale (testo libero)",
    )
    assessed_at = models.DateTimeField(null=True, blank=True)
    plan_due_date = models.DateField(null=True, blank=True)
    critical_process = models.ForeignKey(
        "bia.CriticalProcess",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="risk_assessments",
    )
    # Ciclo di valutazione a cui appartiene il rischio (metodologia di risk management).
    # I rischi precedenti alla revisione stanno nel ciclo `legacy` del loro sito.
    cycle = models.ForeignKey(
        "risk.RiskAssessmentCycle",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="risks",
    )
    # Valori dei campi del metodo superato, conservati per la consultazione in
    # sola lettura quando i campi spariscono dal model.
    legacy_snapshot = models.JSONField(default=dict, blank=True)
    evaluated_in_cycle = models.ForeignKey(
        "risk.RiskAssessmentCycle",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="evaluated_risks",
        help_text="Ultimo ciclo che ha valutato o confermato il rischio",
    )

    # ── Identificazione (procedura §6) ──
    affected_plants = models.ManyToManyField(
        "plants.Plant", blank=True, related_name="inherited_risks",
        help_text="Rischio di gruppo: siti che lo ereditano",
    )
    asset_type = models.CharField(max_length=12, blank=True, default="", db_index=True)
    asset_group_label = models.CharField(max_length=200, blank=True, default="")
    supplier = models.ForeignKey(
        "suppliers.Supplier", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="risk_assessments",
    )
    threat = models.ForeignKey(
        "risk.ThreatCatalogEntry", null=True, blank=True, on_delete=models.PROTECT,
        related_name="risks",
    )
    information_classes = models.ManyToManyField(
        "risk.InformationClass", blank=True, related_name="risks",
    )
    business_objectives = models.ManyToManyField(
        "risk.BusinessObjective", blank=True, related_name="risks",
        help_text="Obiettivi aziendali minacciati (procedura §2): il punto di partenza della valutazione",
    )
    vulnerability = models.TextField(blank=True, default="")
    applicable = models.BooleanField(default=True)
    not_applicable_reason = models.TextField(blank=True, default="")

    # ── Rischio attuale (procedura §7, §8) ──
    probability_method = models.CharField(
        max_length=10, blank=True, default="",
        choices=[("frequenza", "Frequenza"), ("fer", "Fattore di esposizione")],
    )
    probability_rationale = models.TextField(blank=True, default="")
    impact_economic = models.IntegerField(null=True, blank=True, choices=IMPACT_CHOICES)
    impact_legal = models.IntegerField(null=True, blank=True, choices=IMPACT_CHOICES)
    impact_customer = models.IntegerField(null=True, blank=True, choices=IMPACT_CHOICES)
    impact_reputational = models.IntegerField(null=True, blank=True, choices=IMPACT_CHOICES)
    impact_people = models.IntegerField(null=True, blank=True, choices=IMPACT_CHOICES)
    impact_operational = models.IntegerField(null=True, blank=True, choices=IMPACT_CHOICES)
    impact_rationale = models.TextField(blank=True, default="")
    matrix_class = models.CharField(max_length=10, blank=True, default="")
    current_class = models.CharField(max_length=10, blank=True, default="", db_index=True)
    legal_or_contract_violation = models.BooleanField(
        default=False,
        help_text="Violazione di legge, di requisiti VDA ISA o di obblighi di riservatezza: mai accettabile",
    )

    # ── Trattamento e rischio atteso (procedura §9) ──
    treatment_rationale = models.TextField(blank=True, default="")
    expected_probability = models.IntegerField(null=True, blank=True, choices=PROB_CHOICES)
    expected_impact = models.IntegerField(null=True, blank=True, choices=IMPACT_CHOICES)
    expected_class = models.CharField(max_length=10, blank=True, default="")

    # ── NIS2 ──
    nis2_in_scope = models.BooleanField(default=False)
    significant_incident_potential = models.BooleanField(default=False)
    significant_incident_note = models.TextField(blank=True, default="")

    # Conseguenza sugli obiettivi aziendali (procedura §2, §6)
    consequence = models.TextField(blank=True, default="")

    # Area NIS2 Art.21(2)
    nis2_art21_category = models.CharField(
        max_length=20,
        blank=True,
        default="",
        choices=NIS2_ART21_CHOICES,
    )
    impacted_systems = models.TextField(
        blank=True,
        default="",
        help_text="Sistemi/servizi NIS2 impattati (testo libero)",
    )

    class Meta:
        ordering = ["-created_at"]


class RiskMitigationPlan(BaseModel):
    assessment = models.ForeignKey(
        RiskAssessment,
        on_delete=models.CASCADE,
        related_name="mitigation_plans",
    )
    action = models.TextField()
    owner = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    # Alternativa a owner per chi non è utente del portale (testo libero).
    owner_external = models.CharField(max_length=200, blank=True, default="")
    due_date = models.DateField()
    # Collega il piano di mitigazione a un BCP: la mitigazione vale finché il BCP
    # resta "valid" (next_test_date >= oggi) e quindi può perdere valore
    # automaticamente quando il test BCP scade.
    bcp_plan = models.ForeignKey(
        "bcp.BcpPlan",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="risk_mitigation_plans",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    control_instance = models.ForeignKey(
        "controls.ControlInstance",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    expected_effect = models.CharField(
        max_length=12, blank=True, default="",
        choices=[("probabilita", "Probabilità"), ("impatto", "Impatto"), ("entrambi", "Entrambi")],
    )
    # Verifica di efficacia (procedura §9.4, §11.3): solo con tutte le misure
    # verificate il rischio atteso può diventare rischio attuale.
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        "auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="verified_risk_plans",
    )
    verification_note = models.TextField(blank=True, default="")
    # 0 = nessun avviso, 1 = ritardo segnalato, 2 = escalation (procedura §11.3)
    escalation_level = models.SmallIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]


class RiskExistingMeasure(BaseModel):
    """Misura già attuata che incide sul rischio attuale, con la sua efficacia."""

    EFFECTIVENESS_CHOICES = [("alta", "Alta"), ("media", "Media"), ("bassa", "Bassa")]

    risk = models.ForeignKey(RiskAssessment, on_delete=models.CASCADE, related_name="existing_measures")
    control_instance = models.ForeignKey(
        "controls.ControlInstance", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="risk_existing_measures",
    )
    description = models.TextField(blank=True, default="")
    effectiveness = models.CharField(max_length=10, choices=EFFECTIVENESS_CHOICES, default="media")

    class Meta:
        ordering = ["created_at"]


class RiskAcceptance(BaseModel):
    """Accettazione del rischio attuale (procedura §10), con storico.

    Diventa `active` quando hanno firmato tutti i ruoli richiesti dalla policy
    per la classe, c'è il parere favorevole del livello superiore se vincolante
    e, se richiesto, la delibera dell'organo presa in un riesame di direzione.
    Una sola accettazione attiva o in corso per rischio.
    """

    STATUS_CHOICES = [
        ("pending", "In approvazione"),
        ("active", "Attiva"),
        ("rejected", "Respinta"),
        ("revoked", "Revocata"),
        ("expired", "Scaduta"),
    ]
    OPINION_CHOICES = [
        ("not_required", "Non richiesto"),
        ("pending", "In attesa"),
        ("favorable", "Favorevole"),
        ("unfavorable", "Contrario"),
    ]

    risk = models.ForeignKey(RiskAssessment, on_delete=models.CASCADE, related_name="acceptances")
    risk_class = models.CharField(max_length=10)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending", db_index=True)
    required_roles = models.JSONField(default=list, blank=True)
    signatures = models.JSONField(
        default=list, blank=True, help_text="[{role, user_id, at}] — firme raccolte",
    )
    requires_body = models.BooleanField(default=False)
    body = models.ForeignKey(
        "governance.SecurityCommittee", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="risk_acceptances",
    )
    body_resolution_ref = models.CharField(max_length=300, blank=True, default="")
    # Riesame di direzione (completo o mirato) in cui l'organo ha deciso
    # l'accettazione: la delibera è il verbale approvato (procedura §10).
    review = models.ForeignKey(
        "management_review.ManagementReview", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="risk_acceptances",
    )
    rationale = models.TextField()
    expires_on = models.DateField()
    upper_opinion = models.CharField(max_length=12, choices=OPINION_CHOICES, default="not_required")
    opinion_by = models.ForeignKey(
        "auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="risk_acceptance_opinions",
    )
    opinion_at = models.DateTimeField(null=True, blank=True)
    opinion_note = models.TextField(blank=True, default="")
    activated_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    close_reason = models.TextField(blank=True, default="")
    expiry_warned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["risk"],
                condition=models.Q(deleted_at__isnull=True, status__in=["pending", "active"]),
                name="uniq_open_acceptance_per_risk",
            ),
        ]


class RiskLocalImpactReport(BaseModel):
    """Segnalazione di un sito: impatto locale di un rischio di gruppo più alto
    di quello stimato (procedura §4.3)."""

    STATUS_CHOICES = [("aperta", "Aperta"), ("recepita", "Recepita")]

    risk = models.ForeignKey(RiskAssessment, on_delete=models.CASCADE, related_name="local_impact_reports")
    plant = models.ForeignKey("plants.Plant", on_delete=models.CASCADE, related_name="risk_local_impact_reports")
    local_impact = models.IntegerField(choices=IMPACT_CHOICES)
    note = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="aperta")
    acknowledged_by = models.ForeignKey(
        "auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


# ─────────────────────────────────────────────────────────────────────────────
# Metodologia di risk management (revisione post audit TISAX): catalogo minacce,
# classi di informazioni, policy di governo del rischio e cicli di valutazione.
# Le regole di calcolo stanno in services.py (risk_class, resolve_policy, …).
# ─────────────────────────────────────────────────────────────────────────────

ASSET_TYPE_CHOICES = [
    ("IT", "IT"),
    ("OT", "OT"),
    ("SEDE", "Sede"),
    ("PERSONALE", "Personale"),
    ("FORNITORI", "Fornitori"),
    ("PROTOTIPI", "Prototipi"),
]
ASSET_TYPES = [code for code, _ in ASSET_TYPE_CHOICES]

PROTECTION_LEVEL_CHOICES = [
    ("low", "Low"),
    ("normal", "Normal"),
    ("high", "High"),
    ("very_high", "Very high"),
]


class ThreatCatalogEntry(BaseModel):
    """Voce del catalogo minacce di gruppo (procedura §6.3).

    `source=catalog` arriva da `backend/risk_catalogs/threats.json` tramite
    `load_risk_catalog` e non si modifica da UI; `source=custom` sono le voci
    aggiunte dall'organizzazione. Una voce non più usata si disattiva
    (`active=False`), non si cancella: i rischi valutati la referenziano.
    """

    SOURCE_CHOICES = [("catalog", "Catalogo"), ("custom", "Personalizzata")]

    code = models.CharField(max_length=30)
    asset_types = models.JSONField(default=list, help_text="Tipologie di asset a cui si applica")
    cia = models.JSONField(default=list, help_text="Proprietà colpite: C, I, A")
    translations = models.JSONField(default=dict)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="custom")
    catalog_version = models.CharField(max_length=20, blank=True, default="")
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["code"],
                condition=models.Q(deleted_at__isnull=True),
                name="uniq_active_threat_code",
            ),
        ]

    def tr(self, field: str, lang: str = "it", default: str = "") -> str:
        # Ripiego sull'inglese (gruppo multi-paese), poi sull'italiano.
        for cand in (lang, "en", "it"):
            val = (self.translations.get(cand) or {}).get(field)
            if val:
                return val
        return default

    def get_title(self, lang: str = "it") -> str:
        return self.tr("title", lang, default=self.code)

    def __str__(self):
        return f"{self.code} {self.get_title()}"


class BusinessObjective(BaseModel):
    """Obiettivo aziendale da cui parte la valutazione (procedura §2, rilievo
    TISAX: i rischi si valutano a partire dagli obiettivi). Non è un obiettivo
    di sicurezza §6.2 (governance.SecurityObjective): quello è un traguardo
    misurabile che nasce dal trattamento di un rischio.

    `plant` nullo = obiettivo di gruppo, valido per tutti i siti.
    `impact_dimensions` = dimensioni d'impatto con cui si misura il danno
    all'obiettivo: la scheda del rischio le usa per proporlo.
    """

    plant = models.ForeignKey(
        "plants.Plant", null=True, blank=True, on_delete=models.CASCADE,
        related_name="business_objectives",
    )
    code = models.CharField(max_length=30, blank=True, default="", db_index=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    impact_dimensions = models.JSONField(default=list, blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class InformationClass(BaseModel):
    """Classe di informazioni da proteggere (VDA ISA 1.3.1 / 1.3.2, procedura §6.1).

    `plant` nullo = classe di gruppo (es. dati dell'ERP centrale).
    """

    plant = models.ForeignKey(
        "plants.Plant",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="information_classes",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    owner = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_information_classes",
    )
    owner_role = models.CharField(
        max_length=50, blank=True, default="",
        help_text="Ruolo normativo dell'owner (governance.NormativeRole)",
    )
    confidentiality = models.CharField(max_length=10, choices=PROTECTION_LEVEL_CHOICES, default="normal")
    integrity = models.CharField(max_length=10, choices=PROTECTION_LEVEL_CHOICES, default="normal")
    availability = models.CharField(max_length=10, choices=PROTECTION_LEVEL_CHOICES, default="normal")
    critical_processes = models.ManyToManyField(
        "bia.CriticalProcess", blank=True, related_name="information_classes",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class RiskGovernancePolicy(BaseModel):
    """Modello di governo del rischio (procedura §1, §4, §10).

    Una policy di organizzazione (`plant` nullo) più eventuali eccezioni per
    sito: per ogni impostazione vince la più specifica non vuota. Senza alcuna
    policy valgono i default del preset (services.resolve_policy).
    """

    PRESET_CHOICES = [
        ("centralizzato", "Centralizzato"),
        ("federato", "Federato"),
        ("sito_singolo", "Sito singolo"),
    ]

    plant = models.ForeignKey(
        "plants.Plant",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="risk_governance_policies",
    )
    preset = models.CharField(max_length=20, choices=PRESET_CHOICES, default="centralizzato")
    group_register_enabled = models.BooleanField(null=True, blank=True)
    acceptance_matrix = models.JSONField(default=dict, blank=True)
    upper_opinion = models.JSONField(default=dict, blank=True)
    acceptance_max_months = models.JSONField(default=dict, blank=True)
    economic_thresholds = models.JSONField(default=dict, blank=True)
    overdue_escalation_days = models.PositiveIntegerField(null=True, blank=True)
    review_frequency_months = models.PositiveIntegerField(null=True, blank=True)
    approved_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_risk_governance_policies",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["plant_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["plant"],
                condition=models.Q(deleted_at__isnull=True),
                nulls_distinct=False,
                name="uniq_active_risk_governance_policy_per_scope",
            ),
        ]


class RiskAssessmentCycle(BaseModel):
    """Una valutazione completa di un registro (sito o gruppo) — procedura §5, §11.

    `plant` nullo = registro di gruppo. Al più un ciclo aperto (in corso o in
    approvazione) per registro. `legacy` = il registro precedente alla
    revisione della metodologia, archiviato in sola lettura.
    """

    KIND_CHOICES = [
        ("primo", "Primo risk assessment"),
        ("periodico", "Revisione periodica"),
        ("straordinario", "Revisione straordinaria"),
        ("legacy", "Valutazione precedente (metodo superato)"),
    ]
    STATUS_CHOICES = [
        ("in_corso", "In corso"),
        ("in_approvazione", "In approvazione"),
        ("approvato", "Approvato"),
        ("archiviato", "Archiviato"),
    ]
    OPEN_STATUSES = ("in_corso", "in_approvazione")

    plant = models.ForeignKey(
        "plants.Plant",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="risk_cycles",
    )
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    trigger_reason = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="in_corso", db_index=True)
    started_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)
    approved_by_body = models.ForeignKey(
        "governance.SecurityCommittee",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_risk_cycles",
    )
    approval_review = models.ForeignKey(
        "management_review.ManagementReview",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_risk_cycles",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    local_adoption_ref = models.CharField(
        max_length=300, blank=True, default="",
        help_text="Delibera di recepimento dell'organo della società (società estere)",
    )
    snapshot = models.JSONField(
        default=dict, blank=True,
        help_text="Registro congelato all'approvazione: rischi, classi, accettazioni, copertura, policy",
    )

    class Meta:
        ordering = ["-started_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["plant"],
                condition=models.Q(
                    deleted_at__isnull=True,
                    status__in=["in_corso", "in_approvazione"],
                ),
                nulls_distinct=False,
                name="uniq_open_risk_cycle_per_register",
            ),
        ]

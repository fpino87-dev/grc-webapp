from django.db import models

from core.models import BaseModel


class NetworkZone(BaseModel):
    plant = models.ForeignKey("plants.Plant", on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    zone_type = models.CharField(
        max_length=10,
        choices=[("IT", "IT"), ("OT", "OT"), ("DMZ", "DMZ")],
    )
    purdue_level = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["plant_id", "name"]


class Asset(BaseModel):
    plant = models.ForeignKey(
        "plants.Plant",
        on_delete=models.CASCADE,
        related_name="assets",
    )
    name = models.CharField(max_length=200)
    asset_type = models.CharField(
        max_length=5,
        choices=[("IT", "IT"), ("OT", "OT"), ("SW", "SW"), ("FAC", "Impianto")],
    )
    criticality = models.IntegerField(default=1)
    processes = models.ManyToManyField("bia.CriticalProcess", blank=True)
    owner = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    maintainer_supplier = models.ForeignKey(
        "suppliers.Supplier",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="maintained_assets",
        help_text=(
            "Fornitore che manutiene / ha accesso remoto a questo asset. Usato "
            "dal modulo OSINT per escalare gli alert critici dei fornitori con "
            "foothold su asset OT."
        ),
    )
    notes = models.TextField(blank=True)

    # Riferimento change esterno (ticket Jira, ServiceNow, ecc.)
    last_change_ref = models.CharField(
        max_length=100, blank=True,
        help_text="Riferimento ticket esterno es. JIRA-1234, SN-5678",
    )
    last_change_date = models.DateField(
        null=True, blank=True,
        help_text="Data dell'ultimo change registrato",
    )
    last_change_desc = models.CharField(
        max_length=300, blank=True,
        help_text="Descrizione breve del change",
    )
    change_portal_url = models.URLField(
        blank=True,
        help_text="Link diretto al ticket nel portale change management",
    )
    needs_revaluation = models.BooleanField(
        default=False,
        help_text="True se il change richiede rivalutazione dei controlli e del risk assessment collegati",
    )
    needs_revaluation_since = models.DateField(null=True, blank=True)

    # ── Manutenzione periodica ───────────────────────────────────────────────
    # L'asset tiene lo STATO della manutenzione (cadenza, ultima, prossima,
    # esito); l'esecuzione — chi, quando, cosa ha misurato — vive nelle
    # checklist, che sono già datate, firmate e tracciate. Qui non si accumula
    # uno storico: il registro resta un registro.
    MAINTENANCE_RESULT_CHOICES = [
        ("superata", "Superata"),
        ("con_riserve", "Superata con riserve"),
        ("fallita", "Fallita"),
    ]
    maintenance_frequency_months = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text=(
            "Cadenza di manutenzione in mesi; vuoto = nessuna manutenzione "
            "programmata (l'asset non entra nello scadenzario)."
        ),
    )
    last_maintenance_date = models.DateField(null=True, blank=True)
    next_maintenance_date = models.DateField(null=True, blank=True, db_index=True)
    last_maintenance_result = models.CharField(
        max_length=15, choices=MAINTENANCE_RESULT_CHOICES, blank=True
    )
    maintenance_notes = models.TextField(blank=True)
    # Scadenza per cui il promemoria è già stato aperto. Confrontarla con
    # next_maintenance_date rende il giro notturno idempotente senza un flag
    # da azzerare a mano: registrata la manutenzione la prossima scadenza
    # cambia, e l'asset torna da segnalare al momento giusto.
    maintenance_alert_for = models.DateField(null=True, blank=True)

    @property
    def maintenance_is_overdue(self) -> bool:
        from django.utils import timezone
        return bool(
            self.next_maintenance_date
            and self.next_maintenance_date < timezone.localdate()
        )

    @property
    def has_recent_change(self) -> bool:
        """True se c'è stato un change negli ultimi 30 giorni."""
        if not self.last_change_date:
            return False
        from django.utils import timezone
        delta = timezone.localdate() - self.last_change_date
        return delta.days <= 30

    @property
    def change_age_days(self):
        """Giorni dall'ultimo change registrato."""
        if not self.last_change_date:
            return None
        from django.utils import timezone
        return (timezone.localdate() - self.last_change_date).days

    @property
    def risk_score(self):
        ra = self.risk_assessments.filter(
            status="completato", deleted_at__isnull=True
        ).order_by("-assessed_at").first()
        return ra.weighted_score if ra else None

    @property
    def risk_level(self):
        s = self.risk_score
        if s is None:   return "non_valutato"
        if s <= 7:      return "verde"
        if s <= 14:     return "giallo"
        return "rosso"

    class Meta:
        ordering = ["-criticality", "name"]


class AssetIT(Asset):
    fqdn = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    os = models.CharField(max_length=100, blank=True)
    eol_date = models.DateField(null=True, blank=True)
    cve_score_max = models.FloatField(null=True, blank=True)
    internet_exposed = models.BooleanField(default=False)
    deployment_type = models.CharField(
        max_length=10,
        choices=[
            ("on_prem", "On-premise"),
            ("iaas", "IaaS"),
            ("paas", "PaaS"),
            ("saas", "SaaS"),
        ],
        default="on_prem",
        help_text="Modalità di erogazione: on-premise, IaaS, PaaS o SaaS.",
    )
    provider = models.CharField(
        max_length=100,
        blank=True,
        help_text="Cloud/service provider es. Microsoft, AWS, SAP.",
    )
    service_name = models.CharField(
        max_length=150,
        blank=True,
        help_text="Nome del servizio es. Microsoft 365, Salesforce, SAP S/4HANA Cloud.",
    )
    data_classification = models.CharField(
        max_length=20,
        blank=True,
        help_text="Classificazione dati principale (es. internal, confidential, restricted).",
    )

    @property
    def is_eol(self):
        from django.utils import timezone
        return self.eol_date and self.eol_date < timezone.localdate()

    @property
    def exposure_score(self):
        score = 1
        if self.internet_exposed:     score += 2
        if self.cve_score_max and self.cve_score_max >= 7.0: score += 1
        if self.is_eol:               score += 1
        return min(5, score)

    class Meta:
        verbose_name = "Asset IT"


class AssetOT(Asset):
    # Campi di rete: un asset OT raggiungibile da Internet (interfaccia di
    # management, VPN di teleassistenza, ecc.) è un target che il modulo OSINT
    # deve monitorare. Mirror dei campi AssetIT pertinenti.
    fqdn = models.CharField(
        max_length=255, blank=True,
        help_text="Hostname pubblico dell'interfaccia di management/teleassistenza, se esposta.",
    )
    ip_address = models.GenericIPAddressField(
        null=True, blank=True,
        help_text="IP pubblico dell'interfaccia di management, se esposta.",
    )
    internet_exposed = models.BooleanField(
        default=False,
        help_text="L'asset OT è raggiungibile da Internet (condizione di rischio elevato).",
    )
    purdue_level = models.IntegerField()
    category = models.CharField(
        max_length=20,
        choices=[
            ("PLC", "PLC"),
            ("SCADA", "SCADA"),
            ("HMI", "HMI"),
            ("RTU", "RTU"),
            ("sensore", "Sensore"),
            ("altro", "Altro"),
        ],
    )
    patchable = models.BooleanField(default=False)
    patch_block_reason = models.TextField(blank=True)
    maintenance_window = models.CharField(max_length=100, blank=True)
    network_zone = models.ForeignKey(
        NetworkZone,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    vendor = models.CharField(max_length=100, blank=True)

    @property
    def isolation_score(self):
        score = 5
        if self.purdue_level >= 3:  score -= 1
        if self.patchable:          score -= 1
        if self.network_zone and self.network_zone.zone_type == "OT": score -= 1
        return max(1, score)

    class Meta:
        verbose_name = "Asset OT"


class AssetSW(Asset):
    vendor = models.CharField(max_length=100, blank=True)
    version = models.CharField(max_length=50, blank=True)
    approval_status = models.CharField(
        max_length=20,
        choices=[
            ("approvato", "Approvato"),
            ("in_valutazione", "In valutazione"),
            ("deprecato", "Deprecato"),
            ("vietato", "Vietato"),
        ],
        default="in_valutazione",
    )
    license_type = models.CharField(
        max_length=20,
        choices=[
            ("commerciale", "Commerciale"),
            ("open_source", "Open Source"),
            ("saas", "SaaS"),
            ("freeware", "Freeware"),
        ],
        blank=True,
    )
    end_of_support = models.DateField(
        null=True,
        blank=True,
        help_text="Data di fine supporto del vendor (EOS). Alla scadenza viene creato un task.",
    )
    external_ref = models.CharField(
        max_length=200,
        blank=True,
        help_text="Riferimento nel sistema ITAM esterno (es. Lansweeper ID 4521, ServiceNow CI-00123).",
    )
    vendor_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="URL del vendor del software — usato dal modulo OSINT per monitoraggio passivo del dominio fornitore.",
    )

    @property
    def is_eos(self):
        from django.utils import timezone
        return bool(self.end_of_support and self.end_of_support < timezone.localdate())

    @property
    def days_to_eos(self):
        if not self.end_of_support:
            return None
        from django.utils import timezone
        return (self.end_of_support - timezone.localdate()).days

    class Meta:
        verbose_name = "Asset SW"


class AssetFacility(Asset):
    """
    Impianti di supporto: continuità elettrica, antincendio, climatizzazione,
    sicurezza fisica. ISO 27001 li mette esplicitamente in perimetro (A.7 —
    sicurezza fisica e ambientale), ma finora non avevano dove stare: il
    registro conosceva solo IT, OT e software.

    Le misure (autonomia rilevata in una prova, temperatura di sala) NON stanno
    qui: sono rilevazioni e vanno nelle checklist, dove diventano una serie
    storica invece di un campo che qualcuno sovrascrive.
    """

    CATEGORY_CHOICES = [
        ("ups", "UPS / gruppo di continuità"),
        ("gruppo_elettrogeno", "Gruppo elettrogeno"),
        ("antincendio", "Rilevazione / spegnimento incendi"),
        ("climatizzazione", "Climatizzazione sala tecnica"),
        ("controllo_accessi", "Controllo accessi fisici"),
        ("videosorveglianza", "Videosorveglianza"),
        ("altro", "Altro impianto"),
    ]

    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, db_index=True)
    location = models.CharField(
        max_length=200,
        blank=True,
        help_text="Ubicazione fisica: sala server, cabina elettrica, reparto…",
    )
    vendor = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=100, blank=True)
    installation_date = models.DateField(null=True, blank=True)
    # Solo per UPS e gruppi elettrogeni: il dato di targa, contro cui
    # confrontare l'autonomia realmente misurata nelle prove periodiche.
    rated_autonomy_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Autonomia nominale dichiarata dal costruttore (UPS/gruppi elettrogeni).",
    )
    serves_assets = models.ManyToManyField(
        Asset,
        blank=True,
        related_name="supporting_facilities",
        help_text="Asset IT/OT alimentati o protetti da questo impianto.",
    )

    class Meta:
        verbose_name = "Asset Facility"
        verbose_name_plural = "Asset Facility"


class AssetDependency(BaseModel):
    from_asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="dependencies_from",
    )
    to_asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="dependencies_to",
    )
    dep_type = models.CharField(
        max_length=20,
        choices=[
            ("dipende_da", "Dipende da"),
            ("connesso_a", "Connesso a"),
        ],
    )

    class Meta:
        ordering = ["from_asset_id", "to_asset_id"]


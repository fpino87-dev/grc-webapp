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


class Asset(BaseModel):
    plant = models.ForeignKey(
        "plants.Plant",
        on_delete=models.CASCADE,
        related_name="assets",
    )
    name = models.CharField(max_length=200)
    asset_type = models.CharField(
        max_length=5,
        choices=[("IT", "IT"), ("OT", "OT"), ("SW", "SW")],
    )
    criticality = models.IntegerField(default=1)
    processes = models.ManyToManyField("bia.CriticalProcess", blank=True)
    owner = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
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

    @property
    def has_recent_change(self) -> bool:
        """True se c'è stato un change negli ultimi 30 giorni."""
        if not self.last_change_date:
            return False
        from django.utils import timezone
        delta = timezone.now().date() - self.last_change_date
        return delta.days <= 30

    @property
    def change_age_days(self):
        """Giorni dall'ultimo change registrato."""
        if not self.last_change_date:
            return None
        from django.utils import timezone
        return (timezone.now().date() - self.last_change_date).days

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
        return self.eol_date and self.eol_date < timezone.now().date()

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
        return bool(self.end_of_support and self.end_of_support < timezone.now().date())

    @property
    def days_to_eos(self):
        if not self.end_of_support:
            return None
        from django.utils import timezone
        return (self.end_of_support - timezone.now().date()).days

    class Meta:
        verbose_name = "Asset SW"


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


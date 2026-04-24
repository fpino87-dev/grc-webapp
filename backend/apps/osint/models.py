"""Modelli modulo OSINT.

Single-tenant: nessun tenant_id. Settings è singleton.
Tutti i modelli ereditano da `core.models.BaseModel` (UUID, soft delete, audit).
"""
from django.db import models

from apps.notifications.models import EncryptedCharField
from core.models import BaseModel


class EntityType(models.TextChoices):
    MY_DOMAIN = "my_domain", "Dominio interno"
    SUPPLIER = "supplier", "Fornitore"
    ASSET = "asset", "Asset"


class SourceModule(models.TextChoices):
    SITES = "sites", "Siti"
    SUPPLIERS = "suppliers", "Fornitori"
    ASSETS_IT = "assets_it", "Asset IT"
    ASSETS_OT = "assets_ot", "Asset OT"
    ASSETS_SOFTWARE = "assets_software", "Asset Software"


class ScanFrequency(models.TextChoices):
    WEEKLY = "weekly", "Settimanale"
    MONTHLY = "monthly", "Mensile"


class ScanStatus(models.TextChoices):
    RUNNING = "running", "In esecuzione"
    COMPLETED = "completed", "Completato"
    FAILED = "failed", "Fallito"


class SubdomainStatus(models.TextChoices):
    PENDING = "pending", "In attesa"
    INCLUDED = "included", "Incluso"
    IGNORED = "ignored", "Ignorato"


class AlertSeverity(models.TextChoices):
    CRITICAL = "critical", "Critico"
    WARNING = "warning", "Avviso"
    INFO = "info", "Informativo"


class AlertStatus(models.TextChoices):
    NEW = "new", "Nuovo"
    ACKNOWLEDGED = "acknowledged", "Preso in carico"
    RESOLVED = "resolved", "Risolto"
    PENDING_ESCALATION = "pending_escalation", "In attesa di escalation"


class SubdomainAutoInclude(models.TextChoices):
    YES = "yes", "Sì automatico"
    NO = "no", "No automatico"
    ASK = "ask", "Chiedi conferma"


class OsintEntity(BaseModel):
    """Entità monitorata dal modulo OSINT — aggregata dagli altri moduli."""

    entity_type = models.CharField(max_length=20, choices=EntityType.choices)
    source_module = models.CharField(max_length=20, choices=SourceModule.choices)
    source_id = models.UUIDField(help_text="FK UUID all'entità del modulo di origine")
    domain = models.CharField(max_length=255, db_index=True)
    display_name = models.CharField(max_length=255)
    is_nis2_critical = models.BooleanField(default=False)
    is_active = models.BooleanField(
        default=True,
        help_text="False se la sorgente è stata eliminata — preserva lo storico",
    )
    scan_frequency = models.CharField(
        max_length=10,
        choices=ScanFrequency.choices,
        default=ScanFrequency.WEEKLY,
    )

    class Meta:
        unique_together = [("source_module", "source_id", "domain")]
        indexes = [
            models.Index(fields=["entity_type", "is_active"]),
            models.Index(fields=["domain"]),
        ]
        ordering = ["display_name"]

    def __str__(self) -> str:
        return f"{self.display_name} ({self.domain})"


class OsintSubdomain(BaseModel):
    entity = models.ForeignKey(
        OsintEntity, on_delete=models.CASCADE, related_name="subdomains"
    )
    subdomain = models.CharField(max_length=255)
    status = models.CharField(
        max_length=10,
        choices=SubdomainStatus.choices,
        default=SubdomainStatus.PENDING,
    )
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("entity", "subdomain")]
        indexes = [models.Index(fields=["status"])]
        ordering = ["subdomain"]

    def __str__(self) -> str:
        return self.subdomain


class OsintScan(BaseModel):
    entity = models.ForeignKey(
        OsintEntity, on_delete=models.CASCADE, related_name="scans"
    )
    scan_date = models.DateTimeField(auto_now_add=True, db_index=True)
    status = models.CharField(
        max_length=10,
        choices=ScanStatus.choices,
        default=ScanStatus.RUNNING,
    )

    # SSL
    ssl_valid = models.BooleanField(null=True, blank=True)
    ssl_expiry_date = models.DateField(null=True, blank=True)
    ssl_days_remaining = models.IntegerField(null=True, blank=True)
    ssl_issuer = models.CharField(max_length=255, blank=True)
    ssl_wildcard = models.BooleanField(default=False)

    # DNS
    spf_present = models.BooleanField(null=True, blank=True)
    spf_policy = models.CharField(max_length=50, blank=True)
    dmarc_present = models.BooleanField(null=True, blank=True)
    dmarc_policy = models.CharField(max_length=20, blank=True)
    mx_present = models.BooleanField(null=True, blank=True)
    dnssec_enabled = models.BooleanField(null=True, blank=True)

    # WHOIS
    domain_expiry_date = models.DateField(null=True, blank=True)
    domain_registrar = models.CharField(max_length=255, blank=True)
    whois_privacy = models.BooleanField(null=True, blank=True)
    registrar_country = models.CharField(max_length=10, blank=True)

    # Reputazione
    vt_malicious = models.IntegerField(null=True, blank=True)
    vt_suspicious = models.IntegerField(null=True, blank=True)
    abuseipdb_score = models.IntegerField(null=True, blank=True)
    abuseipdb_reports = models.IntegerField(null=True, blank=True)
    otx_pulses = models.IntegerField(null=True, blank=True)
    gsb_status = models.CharField(max_length=20, blank=True)
    in_blacklist = models.BooleanField(default=False)
    blacklist_sources = models.JSONField(default=list, blank=True)

    # Breach (opzionale HIBP, solo my_domain)
    hibp_breaches = models.IntegerField(null=True, blank=True)
    hibp_latest_breach = models.DateField(null=True, blank=True)
    hibp_data_types = models.JSONField(default=list, blank=True)

    # Score
    score_ssl = models.IntegerField(default=0)
    score_dns = models.IntegerField(default=0)
    score_reputation = models.IntegerField(default=0)
    score_grc_context = models.IntegerField(default=0)
    score_total = models.IntegerField(default=0, db_index=True)

    # Errori enricher (per debug): {enricher_name: error_message}
    enricher_errors = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-scan_date"]
        indexes = [
            models.Index(fields=["entity", "-scan_date"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"Scan {self.entity.domain} @ {self.scan_date:%Y-%m-%d}"


class AlertType(models.TextChoices):
    SSL_EXPIRY = "ssl_expiry", "SSL in scadenza"
    SSL_EXPIRED = "ssl_expired", "SSL scaduto"
    BLACKLIST_NEW = "blacklist_new", "Nuovo ingresso in blacklist"
    DMARC_MISSING = "dmarc_missing", "DMARC assente"
    SCORE_CRITICAL = "score_critical", "Score critico"
    SCORE_DEGRADED = "score_degraded", "Score peggiorato"
    NEW_SUBDOMAIN = "new_subdomain", "Nuovo sottodominio"
    BREACH_FOUND = "breach_found", "Breach rilevata"


class OsintAlert(BaseModel):
    entity = models.ForeignKey(
        OsintEntity, on_delete=models.CASCADE, related_name="alerts"
    )
    scan = models.ForeignKey(
        OsintScan, on_delete=models.SET_NULL, null=True, blank=True, related_name="alerts"
    )
    alert_type = models.CharField(max_length=30, choices=AlertType.choices)
    severity = models.CharField(max_length=10, choices=AlertSeverity.choices)
    description = models.TextField()
    status = models.CharField(
        max_length=20, choices=AlertStatus.choices, default=AlertStatus.NEW
    )
    # Nota: UUIDField libero — il modulo OSINT NON modifica Incidents/Tasks;
    # collegamento soft via id (no FK) per rispettare vincolo "non modificare moduli esistenti".
    linked_incident_id = models.UUIDField(null=True, blank=True)
    linked_task_id = models.UUIDField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["entity", "status"]),
            models.Index(fields=["alert_type", "status"]),
            models.Index(fields=["severity"]),
        ]

    def __str__(self) -> str:
        return f"{self.severity}:{self.alert_type} — {self.entity.domain}"


class OsintSettings(BaseModel):
    """Singleton — accedere via `OsintSettings.load()`."""

    score_threshold_critical = models.IntegerField(default=70)
    score_threshold_warning = models.IntegerField(default=50)
    freq_my_domains = models.CharField(
        max_length=10, choices=ScanFrequency.choices, default=ScanFrequency.WEEKLY
    )
    freq_suppliers_critical = models.CharField(
        max_length=10, choices=ScanFrequency.choices, default=ScanFrequency.WEEKLY
    )
    freq_suppliers_other = models.CharField(
        max_length=10, choices=ScanFrequency.choices, default=ScanFrequency.MONTHLY
    )
    subdomain_auto_include = models.CharField(
        max_length=5,
        choices=SubdomainAutoInclude.choices,
        default=SubdomainAutoInclude.ASK,
    )
    anonymization_enabled = models.BooleanField(default=True)

    # API keys opzionali — cifrate a riposo (AES-256 via FERNET_KEY)
    hibp_api_key = EncryptedCharField(max_length=512, blank=True, default="")
    virustotal_api_key = EncryptedCharField(max_length=512, blank=True, default="")
    abuseipdb_api_key = EncryptedCharField(max_length=512, blank=True, default="")
    gsb_api_key = EncryptedCharField(max_length=512, blank=True, default="")
    otx_api_key = EncryptedCharField(max_length=512, blank=True, default="")

    class Meta:
        verbose_name = "OSINT Settings"
        verbose_name_plural = "OSINT Settings"

    def save(self, *args, **kwargs):
        # Singleton: garantisce una sola riga attiva (non soft-deleted).
        if not self.pk:
            existing = OsintSettings.objects.first()
            if existing:
                self.pk = existing.pk
                self.id = existing.id
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "OsintSettings":
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create()
        return obj

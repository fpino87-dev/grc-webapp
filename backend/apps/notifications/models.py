from django.db import models

from core.models import BaseModel


NON_DISATTIVABILI = {"nis2_timer_alert", "risk_red_threshold", "delegation_expiring"}


class NotificationSubscription(BaseModel):
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="notification_subscriptions")
    event_type = models.CharField(max_length=100)
    channel = models.CharField(max_length=50, default="email")
    enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("user", "event_type", "channel")

    def save(self, *args, **kwargs):
        if self.event_type in NON_DISATTIVABILI:
            self.enabled = True  # non può essere disabilitato
        super().save(*args, **kwargs)


from fernet_fields import EncryptedCharField


class EmailConfiguration(BaseModel):
    """
    Configurazione SMTP gestita da UI.
    Una configurazione attiva per organizzazione.
    Le credenziali sono cifrate con AES-256 (Fernet).
    """

    PROVIDER_CHOICES = [
        ("office365", "Microsoft Office 365"),
        ("gmail", "Google Gmail / Workspace"),
        ("smtp_custom", "SMTP Personalizzato"),
    ]

    name = models.CharField(
        max_length=100,
        default="Configurazione principale",
    )
    provider = models.CharField(
        max_length=20,
        choices=PROVIDER_CHOICES,
        default="smtp_custom",
    )
    host = models.CharField(max_length=255)
    port = models.IntegerField(default=587)
    use_tls = models.BooleanField(default=True)
    use_ssl = models.BooleanField(default=False)
    username = models.CharField(max_length=255)
    password = EncryptedCharField(max_length=1024)
    from_email = models.CharField(
        max_length=255,
        help_text="Es: GRC Platform <noreply@azienda.com>",
    )
    active = models.BooleanField(default=True)
    last_test_at = models.DateTimeField(null=True, blank=True)
    last_test_ok = models.BooleanField(null=True, blank=True)
    last_test_error = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        """Una sola config attiva alla volta."""
        if self.active:
            EmailConfiguration.objects.exclude(pk=self.pk).update(active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active(cls):
        return cls.objects.filter(active=True, deleted_at__isnull=True).first()

    # Preset per provider comuni
    PROVIDER_PRESETS = {
        "office365": {
            "host": "smtp.office365.com",
            "port": 587,
            "use_tls": True,
            "use_ssl": False,
        },
        "gmail": {
            "host": "smtp.gmail.com",
            "port": 587,
            "use_tls": True,
            "use_ssl": False,
        },
    }


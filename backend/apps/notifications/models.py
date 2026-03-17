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


import base64
import os

from cryptography.fernet import Fernet
from django.conf import settings
from django.db.models import TextField


def _get_fernet():
    key = getattr(settings, "FERNET_KEY", None)
    if not key:
        # derive a stable key from SECRET_KEY
        import hashlib
        raw = settings.SECRET_KEY.encode()
        digest = hashlib.sha256(raw).digest()
        key = base64.urlsafe_b64encode(digest)
    elif isinstance(key, str):
        key = key.encode()
    return Fernet(key)


class EncryptedCharField(TextField):
    """Transparent AES-128 (Fernet) encryption. Django 5 compatible."""

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        try:
            return _get_fernet().decrypt(value.encode()).decode()
        except Exception:
            return value  # already plaintext (legacy) or unreadable

    def get_prep_value(self, value):
        if value is None:
            return value
        try:
            # If already encrypted (starts with 'gAAAAA') skip re-encryption
            _get_fernet().decrypt(value.encode())
            return value
        except Exception:
            return _get_fernet().encrypt(value.encode()).decode()


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
    use_auth = models.BooleanField(
        default=True,
        help_text="Disattiva per relay SMTP senza autenticazione (es. porta 25 interno)",
    )
    username = models.CharField(max_length=255, blank=True, default="")
    password = EncryptedCharField(max_length=1024, blank=True, default="")
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


# ── Definizione profili ───────────────────────────────

NOTIFICATION_PROFILES = {
    "silenzioso": {
        "label":       "Silenzioso",
        "description": "Nessuna notifica email. Solo in-app.",
        "events":      [],
    },
    "essenziale": {
        "label":       "Essenziale",
        "description": "Solo eventi critici che richiedono azione immediata.",
        "events": [
            "risk_red",
            "finding_major",
            "incident_nis2",
            "role_expiring",
            "role_vacant",
        ],
    },
    "standard": {
        "label":       "Standard",
        "description": "Essenziale + eventi operativi quotidiani. "
                       "Consigliato per la maggior parte dei ruoli.",
        "events": [
            "risk_red",
            "finding_major",
            "finding_minor",
            "incident_nis2",
            "incident_closed",
            "role_expiring",
            "role_vacant",
            "task_assigned",
            "task_overdue",
            "evidence_expired",
            "bcp_test_failed",
            "document_approval",
        ],
    },
    "completo": {
        "label":       "Completo",
        "description": "Tutti gli eventi. Consigliato per CISO e Compliance Officer.",
        "events": [
            "risk_red",
            "finding_major",
            "finding_minor",
            "incident_nis2",
            "incident_closed",
            "role_expiring",
            "role_vacant",
            "task_assigned",
            "task_overdue",
            "evidence_expired",
            "bcp_test_failed",
            "document_approval",
            "pdca_blocked",
            "supplier_assessment",
            "management_review",
            "risk_accepted",
        ],
    },
}

DEFAULT_ROLE_PROFILES = {
    "ciso":               "completo",
    "compliance_officer": "completo",
    "risk_manager":       "standard",
    "plant_manager":      "standard",
    "control_owner":      "essenziale",
    "internal_auditor":   "essenziale",
    "external_auditor":   "silenzioso",
    "nis2_contact":       "standard",
    "isms_manager":       "completo",
    "dpo":                "standard",
}

EVENT_LABELS = {
    "risk_red":            "Rischio critico (score > soglia)",
    "finding_major":       "Finding Major NC aperto",
    "finding_minor":       "Finding Minor NC aperto",
    "incident_nis2":       "Incidente NIS2 rilevato",
    "incident_closed":     "Incidente chiuso",
    "role_expiring":       "Ruolo normativo in scadenza",
    "role_vacant":         "Ruolo obbligatorio vacante",
    "task_assigned":       "Task assegnato",
    "task_overdue":        "Task scaduto",
    "evidence_expired":    "Evidenza scaduta",
    "bcp_test_failed":     "Test BCP fallito o parziale",
    "document_approval":   "Documento in attesa approvazione",
    "pdca_blocked":        "PDCA bloccato oltre 30 giorni",
    "supplier_assessment": "Assessment fornitore completato",
    "management_review":   "Revisione direzione da approvare",
    "risk_accepted":       "Rischio formalmente accettato",
}

ROLE_LABELS = {
    "ciso":               "CISO",
    "compliance_officer": "Compliance Officer",
    "risk_manager":       "Risk Manager",
    "plant_manager":      "Plant Manager",
    "control_owner":      "Control Owner",
    "internal_auditor":   "Auditor Interno",
    "external_auditor":   "Auditor Esterno",
    "nis2_contact":       "Contatto NIS2",
    "isms_manager":       "ISMS Manager",
    "dpo":                "DPO",
}


class NotificationRoleProfile(BaseModel):
    """
    Profilo di notifica assegnato a un ruolo GRC.
    Una riga per ogni ruolo — determina quali eventi generano email.
    """
    grc_role = models.CharField(
        max_length=50,
        unique=True,
        help_text="Codice ruolo GRC es. ciso, risk_manager",
    )
    profile = models.CharField(
        max_length=20,
        choices=[
            ("silenzioso", "Silenzioso"),
            ("essenziale", "Essenziale"),
            ("standard",   "Standard"),
            ("completo",   "Completo"),
            ("custom",     "Personalizzato"),
        ],
        default="standard",
    )
    custom_events = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista eventi attivi se profilo = custom",
    )
    enabled = models.BooleanField(
        default=True,
        help_text="False = nessuna notifica per questo ruolo",
    )

    class Meta:
        ordering = ["grc_role"]

    def get_active_events(self) -> list:
        if not self.enabled:
            return []
        if self.profile == "custom":
            return self.custom_events
        return NOTIFICATION_PROFILES.get(self.profile, {}).get("events", [])

    def __str__(self):
        return f"{self.grc_role} → {self.profile}"

    @classmethod
    def get_or_create_defaults(cls):
        created = 0
        for role, profile in DEFAULT_ROLE_PROFILES.items():
            _, c = cls.objects.get_or_create(
                grc_role=role,
                defaults={"profile": profile, "enabled": True},
            )
            if c:
                created += 1
        return created


# ── NotificationRule (legacy — mantenuto per compatibilità) ──────────────────

EVENT_TYPES = [
    ("risk_red", "Rischio critico (score > soglia)"),
    ("finding_major", "Finding Major NC aperto"),
    ("finding_minor", "Finding Minor NC aperto"),
    ("incident_nis2", "Incidente NIS2 rilevato"),
    ("incident_closed", "Incidente chiuso"),
    ("task_assigned", "Task assegnato"),
    ("task_overdue", "Task scaduto"),
    ("evidence_expired", "Evidenza scaduta"),
    ("document_approval", "Documento in attesa approvazione"),
    ("role_expiring", "Ruolo normativo in scadenza"),
    ("bcp_test_failed", "Test BCP fallito"),
    ("pdca_blocked", "PDCA bloccato > 30 giorni"),
    ("management_review", "Revisione direzione da approvare"),
    ("supplier_assessment", "Assessment fornitore completato"),
]

SCOPE_TYPES = [
    ("org", "Tutta l'organizzazione"),
    ("bu", "Business Unit"),
    ("plant", "Sito specifico"),
]


class NotificationRule(BaseModel):
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    enabled = models.BooleanField(default=True)
    recipient_roles = models.JSONField(default=list)
    scope_type = models.CharField(max_length=10, choices=SCOPE_TYPES, default="org")
    scope_bu = models.ForeignKey(
        "plants.BusinessUnit", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="notification_rules",
    )
    scope_plant = models.ForeignKey(
        "plants.Plant", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="notification_rules",
    )
    channel = models.CharField(max_length=10, choices=[("email", "Email")], default="email")

    class Meta:
        ordering = ["event_type"]
        unique_together = ["event_type", "scope_type", "scope_bu", "scope_plant"]

    def __str__(self):
        return f"{self.event_type} → {self.recipient_roles}"


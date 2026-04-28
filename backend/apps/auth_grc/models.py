import hashlib
import secrets

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel


class GrcRole(models.TextChoices):
    SUPER_ADMIN = "super_admin", _("Super Admin")
    COMPLIANCE_OFFICER = "compliance_officer", _("Compliance Officer")
    RISK_MANAGER = "risk_manager", _("Risk Manager")
    PLANT_MANAGER = "plant_manager", _("Plant Manager")
    CONTROL_OWNER = "control_owner", _("Control Owner")
    INTERNAL_AUDITOR = "internal_auditor", _("Auditor Interno")
    EXTERNAL_AUDITOR = "external_auditor", _("Auditor Esterno")


class UserPlantAccess(BaseModel):
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="plant_access",
    )
    role = models.CharField(max_length=50, choices=GrcRole.choices)
    scope_type = models.CharField(
        max_length=20,
        choices=[
            ("org", "Org"),
            ("bu", "BU"),
            ("plant_list", "Lista"),
            ("single_plant", "Plant"),
        ],
    )
    scope_bu = models.ForeignKey(
        "plants.BusinessUnit",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    scope_plants = models.ManyToManyField("plants.Plant", blank=True)
    framework_filter = ArrayField(models.CharField(max_length=50), default=list, blank=True)


class ExternalAuditorToken(BaseModel):
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="auditor_tokens",
    )
    token_hash = models.CharField(max_length=64, unique=True)
    plant = models.ForeignKey("plants.Plant", on_delete=models.CASCADE)
    framework_filter = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    issued_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="issued_tokens",
    )

    @classmethod
    def create_token(cls, user, plant, framework_filter, valid_days, issued_by):
        from django.utils import timezone

        raw = secrets.token_urlsafe(32)
        hashed = hashlib.sha256(raw.encode()).hexdigest()
        obj = cls.objects.create(
            user=user,
            plant=plant,
            framework_filter=framework_filter,
            token_hash=hashed,
            valid_from=timezone.now(),
            valid_until=timezone.now() + timezone.timedelta(days=valid_days),
            issued_by=issued_by,
        )
        return obj, raw  # raw mostrato UNA SOLA VOLTA

    def revoke(self):
        from django.utils import timezone

        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at"])

    @property
    def is_valid(self):
        from django.utils import timezone

        n = timezone.now()
        return self.revoked_at is None and self.valid_from <= n <= self.valid_until


def compute_device_fingerprint(fingerprint_source: str) -> str:
    """
    Hash server-side del fingerprint del browser (newfix S8).

    `fingerprint_source` deve essere costruito dal chiamante come
    `User-Agent || \\n || Accept-Language` (vedi `core.jwt._fingerprint_source`).
    Il SECRET_KEY del backend e' incluso nell'hash come pepper: senza il
    secret, un attaccante che ha solo il device_token non puo' ricalcolare
    l'hash atteso anche se conosce UA/lingua della vittima.

    Restituisce hex SHA-256 a 64 char (compatibile con il campo esistente).
    """
    from django.conf import settings
    if not fingerprint_source:
        return ""
    pepper = getattr(settings, "SECRET_KEY", "")
    payload = f"{fingerprint_source}\x00{pepper}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class TrustedDevice(BaseModel):
    """
    Dispositivo fidato: memorizza il token (hashed) per saltare MFA per 30 giorni.
    Il token grezzo viene restituito UNA SOLA VOLTA al frontend e poi dimenticato.

    newfix S8 — token legato a fingerprint (User-Agent + Accept-Language +
    SECRET_KEY pepper). Un device_token rubato via XSS non e' utilizzabile da
    un browser/lingua diversi. Su rotazione password tutti i TrustedDevice
    vengono revocati (signal in apps.auth_grc.signals).
    """
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="trusted_devices",
    )
    token_hash = models.CharField(max_length=64, db_index=True)
    device_name = models.CharField(max_length=200, blank=True)
    expires_at = models.DateTimeField()
    # newfix S8 — hash del fingerprint del browser (UA + Accept-Language +
    # SECRET_KEY). Vuoto solo per record legacy pre-S8 che non sono piu'
    # accettati da `verify()`.
    fingerprint_hash = models.CharField(max_length=64, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    @classmethod
    def create_for_user(cls, user, device_name="", fingerprint_source=""):
        from django.utils import timezone
        raw = secrets.token_urlsafe(32)
        hashed = hashlib.sha256(raw.encode()).hexdigest()
        obj = cls.objects.create(
            user=user,
            token_hash=hashed,
            device_name=device_name[:200],
            expires_at=timezone.now() + timezone.timedelta(days=30),
            fingerprint_hash=compute_device_fingerprint(fingerprint_source),
        )
        return obj, raw  # raw mostrato UNA SOLA VOLTA

    @classmethod
    def verify(cls, user, raw_token: str, fingerprint_source: str = "") -> bool:
        """
        Verifica un device_token. newfix S8: richiede anche che il fingerprint
        della richiesta corrente coincida con quello salvato all'emissione.
        Record legacy senza fingerprint_hash NON sono piu' accettati: forzano
        un nuovo step MFA (degradazione di sicurezza voluta dopo l'upgrade).
        """
        from django.utils import timezone
        if not raw_token:
            return False
        hashed = hashlib.sha256(raw_token.encode()).hexdigest()
        expected_fp = compute_device_fingerprint(fingerprint_source)
        if not expected_fp:
            # Senza UA/lingua nella request non possiamo bindare: rifiuta.
            return False
        return cls.objects.filter(
            user=user,
            token_hash=hashed,
            fingerprint_hash=expected_fp,
            expires_at__gt=timezone.now(),
        ).exists()

    def revoke(self):
        self.soft_delete()

    @classmethod
    def revoke_all_for_user(cls, user) -> int:
        """
        Revoca (soft-delete) tutti i TrustedDevice di un utente. Usata dal
        signal di cambio password e da MFA disable. Restituisce il numero di
        record toccati.
        """
        from django.utils import timezone
        return cls.objects.filter(user=user).update(deleted_at=timezone.now())


COMPETENCY_LEVEL_CHOICES = [
    (1, "1 — Awareness"),
    (2, "2 — Practitioner"),
    (3, "3 — Expert"),
]

EVIDENCE_TYPE_CHOICES = [
    ("certification",  "Certificazione"),
    ("training",       "Training completato"),
    ("experience",     "Esperienza documentata"),
    ("assessment",     "Assessment interno"),
]


class RoleCompetencyRequirement(BaseModel):
    """Competenze richieste per ogni ruolo GRC. ISO 27001 clausola 7.2."""
    grc_role = models.CharField(max_length=50)
    competency = models.CharField(max_length=200)
    required_level = models.IntegerField(choices=COMPETENCY_LEVEL_CHOICES, default=2)
    evidence_type = models.CharField(
        max_length=20, choices=EVIDENCE_TYPE_CHOICES, default="training"
    )
    mandatory = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ["grc_role", "competency"]
        ordering = ["grc_role", "competency"]


class UserCompetency(BaseModel):
    """Competenza effettiva di un utente."""
    user = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE,
        related_name="competencies"
    )
    competency = models.CharField(max_length=200)
    level = models.IntegerField(choices=COMPETENCY_LEVEL_CHOICES, default=1)
    evidence = models.ForeignKey(
        "documents.Evidence",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="competency_evidences",
    )
    evidence_type = models.CharField(
        max_length=20, choices=EVIDENCE_TYPE_CHOICES, default="training"
    )
    certification_body = models.CharField(max_length=200, blank=True)
    obtained_at = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    verified_by = models.ForeignKey(
        "auth.User", null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_competencies",
    )

    class Meta:
        unique_together = ["user", "competency"]
        ordering = ["user", "competency"]

    @property
    def is_valid(self) -> bool:
        from django.utils import timezone
        if not self.valid_until:
            return True
        return self.valid_until >= timezone.now().date()


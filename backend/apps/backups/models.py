from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel


class BackupRecord(BaseModel):
    class Status(models.TextChoices):
        PENDING   = "pending",   _("In attesa")
        RUNNING   = "running",   _("In corso")
        COMPLETED = "completed", _("Completato")
        FAILED    = "failed",    _("Fallito")
        RESTORED  = "restored",  _("Ripristinato")

    class BackupType(models.TextChoices):
        AUTO   = "auto",   _("Automatico")
        MANUAL = "manual", _("Manuale")

    filename      = models.CharField(max_length=255, blank=True)
    size_bytes    = models.BigIntegerField(null=True, blank=True)
    status        = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.PENDING, db_index=True,
    )
    backup_type   = models.CharField(
        max_length=10, choices=BackupType.choices,
        default=BackupType.MANUAL,
    )
    notes         = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    completed_at  = models.DateTimeField(null=True, blank=True)
    # newfix R4: True se il file pg_dump e' cifrato AES-256-GCM at rest.
    encrypted     = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Backup"
        verbose_name_plural = "Backup"

    def __str__(self):
        return f"{self.filename} [{self.status}]"

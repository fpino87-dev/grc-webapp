"""Centro Operativo (M21) — persistenza (Step 2).

Gli insight restano **calcolati al volo** dagli advisor (sono la verità corrente,
mai stantia). La persistenza serve a:
- ricordare le **azioni utente** (snooze / rischio accettato / nota / owner) per
  non ri-mostrare ciò che è stato gestito → anti alert-fatigue;
- storicizzare la **postura** (`PostureSnapshot`) per il trend nel tempo.
"""
from django.db import models

from core.models import BaseModel


class InsightStatus(models.TextChoices):
    OPEN = "open", "Aperto"
    SNOOZED = "snoozed", "Rimandato"
    ACCEPTED_RISK = "accepted_risk", "Rischio accettato"
    RESOLVED = "resolved", "Risolto"


class InsightState(BaseModel):
    """Stato persistente di un insight, identificato dal suo `fingerprint`.

    Un solo record per fingerprint: quando l'insight scompare dallo scan corrente
    viene auto-risolto; se ricompare, lo stesso record torna `open` (storia
    conservata via created_at/updated_at)."""

    fingerprint = models.CharField(max_length=32, unique=True, db_index=True)
    # Snapshot per filtrare/mostrare senza ricalcolare (allineati a ogni sync).
    code = models.CharField(max_length=64)
    module = models.CharField(max_length=40, blank=True)
    area = models.CharField(max_length=20, blank=True)
    severity = models.CharField(max_length=10, blank=True)
    plant_id = models.UUIDField(null=True, blank=True, db_index=True)
    params_snapshot = models.JSONField(default=dict, blank=True)

    status = models.CharField(max_length=15, choices=InsightStatus.choices, default=InsightStatus.OPEN)
    owner_role = models.CharField(max_length=40, blank=True)
    snoozed_until = models.DateField(null=True, blank=True)
    accepted_until = models.DateField(null=True, blank=True)
    note = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["code", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.code} [{self.status}] {self.fingerprint}"

    def is_suppressed(self, today) -> bool:
        """True se l'insight non va mostrato nella lista principale ora
        (snooze/accettazione ancora validi). Scaduto → torna visibile."""
        if self.status == InsightStatus.SNOOZED:
            return self.snoozed_until is None or self.snoozed_until >= today
        if self.status == InsightStatus.ACCEPTED_RISK:
            return self.accepted_until is None or self.accepted_until >= today
        return False


class PostureSnapshot(BaseModel):
    """Fotografia periodica della postura (per il trend). `plant_id` null = org."""

    plant_id = models.UUIDField(null=True, blank=True, db_index=True)
    taken_on = models.DateField(db_index=True)
    total = models.IntegerField(default=0)
    areas = models.JSONField(default=dict, blank=True)   # {area: {score, critical, warning, info}}
    counts = models.JSONField(default=dict, blank=True)  # {critical, warning, info, total}

    class Meta:
        ordering = ["-taken_on"]
        constraints = [
            models.UniqueConstraint(fields=["plant_id", "taken_on"], name="cockpit_posture_one_per_day"),
        ]

    def __str__(self) -> str:
        return f"Posture {self.plant_id or 'org'} @ {self.taken_on} = {self.total}"

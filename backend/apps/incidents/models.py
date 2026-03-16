from django.db import models

from core.models import BaseModel


class Incident(BaseModel):
    plant = models.ForeignKey("plants.Plant", on_delete=models.CASCADE, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    detected_at = models.DateTimeField()
    severity = models.CharField(
        max_length=10,
        choices=[("bassa", "bassa"), ("media", "media"), ("alta", "alta"), ("critica", "critica")],
        db_index=True,
    )
    nis2_notifiable = models.CharField(
        max_length=20,
        choices=[("si", "si"), ("no", "no"), ("da_valutare", "da_valutare")],
        default="da_valutare",
        db_index=True,
    )
    assets = models.ManyToManyField("assets.Asset", blank=True)
    status = models.CharField(
        max_length=20,
        choices=[("aperto", "aperto"), ("in_analisi", "in_analisi"), ("chiuso", "chiuso")],
        default="aperto",
        db_index=True,
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="closed_incidents",
    )


class IncidentNotification(BaseModel):
    incident = models.ForeignKey(
        Incident,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    channel = models.CharField(max_length=50)
    sent_at = models.DateTimeField(null=True, blank=True)
    payload = models.JSONField(default=dict)


class RCA(BaseModel):
    incident = models.OneToOneField(
        Incident,
        on_delete=models.CASCADE,
        related_name="rca",
    )
    summary = models.TextField()
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_rca",
    )


from django.db import models

from core.models import BaseModel


class PdcaCycle(BaseModel):
    plant = models.ForeignKey("plants.Plant", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    trigger_type = models.CharField(max_length=50)
    trigger_source_id = models.UUIDField(null=True, blank=True)
    scope_type = models.CharField(max_length=50, default="custom")
    scope_id = models.UUIDField(null=True, blank=True)
    fase_corrente = models.CharField(
        max_length=10,
        choices=[("plan", "PLAN"), ("do", "DO"), ("check", "CHECK"), ("act", "ACT")],
        default="plan",
    )


class PdcaPhase(BaseModel):
    cycle = models.ForeignKey(PdcaCycle, on_delete=models.CASCADE, related_name="phases")
    phase = models.CharField(
        max_length=10,
        choices=[("plan", "PLAN"), ("do", "DO"), ("check", "CHECK"), ("act", "ACT")],
    )
    notes = models.TextField(blank=True)


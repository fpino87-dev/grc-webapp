from django.contrib.auth import get_user_model
from django.db import models

from core.models import BaseModel

User = get_user_model()


class PdcaCycle(BaseModel):
    plant = models.ForeignKey("plants.Plant", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    trigger_type = models.CharField(max_length=50)
    trigger_source_id = models.UUIDField(null=True, blank=True)
    scope_type = models.CharField(max_length=50, default="custom")
    scope_id = models.UUIDField(null=True, blank=True)
    fase_corrente = models.CharField(
        max_length=10,
        choices=[
            ("plan", "PLAN"), ("do", "DO"), ("check", "CHECK"),
            ("act", "ACT"), ("chiuso", "Chiuso"),
        ],
        default="plan",
    )
    act_description = models.TextField(
        blank=True,
        help_text="Descrizione standardizzazione — obbligatoria per chiudere",
    )
    check_outcome = models.CharField(
        max_length=20,
        blank=True,
        help_text="Esito CHECK: ok/partial/ko — se ko apre nuovo ciclo",
    )
    reopened_as = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reopened_from",
        help_text="Se CHECK=ko questo ciclo ha generato un nuovo PLAN",
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="closed_pdca_cycles",
    )


class PdcaPhase(BaseModel):
    cycle = models.ForeignKey(PdcaCycle, on_delete=models.CASCADE, related_name="phases")
    phase = models.CharField(
        max_length=10,
        choices=[("plan", "PLAN"), ("do", "DO"), ("check", "CHECK"), ("act", "ACT")],
    )
    notes = models.TextField(blank=True)
    # Contenuto obbligatorio per avanzare alla fase successiva
    evidence = models.ForeignKey(
        "documents.Evidence",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pdca_phases",
        help_text="Obbligatoria per fase DO",
    )
    outcome = models.CharField(
        max_length=20,
        choices=[
            ("ok", "Efficace"),
            ("partial", "Parzialmente efficace"),
            ("ko", "Non efficace"),
        ],
        blank=True,
        help_text="Obbligatorio per fase CHECK",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="completed_pdca_phases",
    )


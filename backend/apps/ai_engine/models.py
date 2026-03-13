import uuid

from django.db import models


class AiInteractionLog(models.Model):
    """Log append-only — human-in-the-loop obbligatorio per ogni output AI."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    user_id = models.UUIDField()
    function = models.CharField(max_length=50)
    module_source = models.CharField(max_length=5)
    entity_id = models.UUIDField()
    model_used = models.CharField(max_length=100)
    input_hash = models.CharField(max_length=64)  # SHA256 — MAI il testo
    output_ai = models.TextField()
    output_human_final = models.TextField(null=True, blank=True)
    delta = models.JSONField(null=True, blank=True)
    confirmed_by_id = models.UUIDField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    ignored = models.BooleanField(default=False)

    class Meta:
        db_table = "ai_interaction_log"
        ordering = ["-created_at"]


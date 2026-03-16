import hashlib
import json
import uuid

from django.db import models, transaction


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp_utc = models.DateTimeField(auto_now_add=True, db_index=True)
    user_id = models.UUIDField()
    user_email_at_time = models.CharField(max_length=255)
    user_role_at_time = models.CharField(max_length=50, blank=True)
    action_code = models.CharField(max_length=100, db_index=True)
    level = models.CharField(max_length=2, choices=[("L1", "L1"), ("L2", "L2"), ("L3", "L3")])
    entity_type = models.CharField(max_length=50, db_index=True)
    entity_id = models.UUIDField(db_index=True)
    payload = models.JSONField()
    prev_hash = models.CharField(max_length=64)
    record_hash = models.CharField(max_length=64)

    class Meta:
        db_table = "audit_log"
        ordering = ["-timestamp_utc"]


def _compute_hash(payload: dict, prev_hash: str) -> str:
    content = json.dumps(payload, sort_keys=True, default=str) + prev_hash
    return hashlib.sha256(content.encode()).hexdigest()


def _get_prev_hash(entity_type: str) -> str:
    # Usa SELECT ... FOR UPDATE per serializzare la catena hash per entity_type
    last = (
        AuditLog.objects.select_for_update()
        .filter(entity_type=entity_type)
        .order_by("-timestamp_utc")
        .first()
    )
    return last.record_hash if last else "0" * 64


@transaction.atomic
def log_action(*, user, action_code: str, level: str, entity, payload: dict) -> AuditLog:
    entity_type = entity.__class__.__name__.lower()
    prev_hash = _get_prev_hash(entity_type)
    record_hash = _compute_hash(payload, prev_hash)
    return AuditLog.objects.create(
        user_id=user.pk,
        user_email_at_time=user.email,
        action_code=action_code,
        level=level,
        entity_type=entity_type,
        entity_id=str(entity.pk),
        payload=payload,
        prev_hash=prev_hash,
        record_hash=record_hash,
    )


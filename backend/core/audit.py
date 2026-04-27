import hashlib
import json
import uuid

from django.db import models, transaction
from django.utils import timezone


def _pseudonymize_email(email: str) -> str:
    """
    Pseudonimizza l'email per l'audit trail (GDPR Art. 25 — privacy by design).
    Mantiene la parte locale visibile fino a 3 char + dominio oscurato,
    sufficiente per auditing senza esporre l'indirizzo completo.
    Esempio: "mario.rossi@azienda.com" → "mar***@***.com"
    """
    if not email or "@" not in email:
        return "***"
    local, domain = email.rsplit("@", 1)
    local_masked = local[:3] + "***" if len(local) > 3 else "***"
    domain_parts = domain.rsplit(".", 1)
    if len(domain_parts) == 2:
        domain_masked = "***." + domain_parts[1]
    else:
        domain_masked = "***"
    return f"{local_masked}@{domain_masked}"


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Default = now(); il valore reale è impostato esplicitamente da log_action
    # per essere incluso nel calcolo dell'hash v2 (auto_now_add lo sovrascriverebbe).
    timestamp_utc = models.DateTimeField(default=timezone.now, db_index=True)
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
    # v1 = hash su (payload, prev_hash) — debole, solo record storici.
    # v2 = hash su (user_id, action_code, level, entity_type, entity_id, timestamp_utc, payload, prev_hash) — tamper-evident anche su user_id/action_code.
    hash_version = models.CharField(max_length=4, default="v2")

    class Meta:
        db_table = "audit_log"
        ordering = ["-timestamp_utc"]


def _compute_hash_v1(payload: dict, prev_hash: str) -> str:
    """Legacy: usato solo per verificare record con hash_version='v1'."""
    content = json.dumps(payload, sort_keys=True, default=str) + prev_hash
    return hashlib.sha256(content.encode()).hexdigest()


def _compute_hash_v2(
    *,
    user_id,
    action_code: str,
    level: str,
    entity_type: str,
    entity_id,
    timestamp_utc,
    payload: dict,
    prev_hash: str,
) -> str:
    """
    Hash che lega tutti i campi immutabili del record. Modificare qualunque
    di user_id/action_code/level/entity_type/entity_id/timestamp invalida la catena.
    """
    content = json.dumps(
        {
            "user_id": str(user_id),
            "action_code": action_code,
            "level": level,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "timestamp_utc": timestamp_utc.isoformat() if timestamp_utc else "",
            "payload": payload,
        },
        sort_keys=True,
        default=str,
    ) + prev_hash
    return hashlib.sha256(content.encode()).hexdigest()


def compute_record_hash(log: "AuditLog") -> str:
    """
    Ricalcola l'hash atteso per un AuditLog esistente, secondo la sua hash_version.
    Usato dal verifier di integrità.
    """
    if log.hash_version == "v2":
        return _compute_hash_v2(
            user_id=log.user_id,
            action_code=log.action_code,
            level=log.level,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            timestamp_utc=log.timestamp_utc,
            payload=log.payload,
            prev_hash=log.prev_hash,
        )
    return _compute_hash_v1(log.payload, log.prev_hash)


def _get_prev_hash(entity_type: str) -> str:
    # Usa SELECT ... FOR UPDATE per serializzare la catena hash per entity_type
    last = (
        AuditLog.objects.select_for_update()
        .filter(entity_type=entity_type)
        .order_by("-timestamp_utc")
        .first()
    )
    return last.record_hash if last else "0" * 64


def _pk_to_uuid(pk) -> uuid.UUID:
    """Converte qualsiasi pk (UUID o intero) in uuid.UUID per il campo entity_id/user_id."""
    if isinstance(pk, uuid.UUID):
        return pk
    try:
        return uuid.UUID(str(pk))
    except (ValueError, AttributeError):
        return uuid.UUID(int=int(pk))


@transaction.atomic
def log_action(*, user, action_code: str, level: str, entity, payload: dict) -> AuditLog:
    from django.utils import timezone

    entity_type = entity.__class__.__name__.lower()
    prev_hash = _get_prev_hash(entity_type)
    user_id = _pk_to_uuid(user.pk)
    entity_id = _pk_to_uuid(entity.pk)
    # Usa now() per il calcolo dell'hash; auto_now_add scriverà lo stesso valore
    # con tolleranza di pochi microsecondi: il verifier confronta entrambe le rotte
    # tramite il campo timestamp_utc effettivamente persistito (vedi sotto).
    timestamp_utc = timezone.now()
    record_hash = _compute_hash_v2(
        user_id=user_id,
        action_code=action_code,
        level=level,
        entity_type=entity_type,
        entity_id=entity_id,
        timestamp_utc=timestamp_utc,
        payload=payload,
        prev_hash=prev_hash,
    )
    return AuditLog.objects.create(
        user_id=user_id,
        # Email pseudonimizzata (GDPR Art. 25 — privacy by design).
        # L'identità completa è ricavabile tramite user_id se necessario per audit legale.
        user_email_at_time=_pseudonymize_email(user.email),
        user_role_at_time=getattr(user, "role", "") or "",
        action_code=action_code,
        level=level,
        entity_type=entity_type,
        entity_id=entity_id,
        timestamp_utc=timestamp_utc,
        payload=payload,
        prev_hash=prev_hash,
        record_hash=record_hash,
        hash_version="v2",
    )


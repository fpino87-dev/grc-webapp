import pytest

from core.audit import AuditLog, compute_record_hash, log_action


@pytest.mark.django_db
def test_hash_chain_valid(co_user, plant_nis2):
    """Catena hash tamper-evident (S2): include user_id, action_code, level,
    entity_type, entity_id, timestamp_utc, payload — vedi core.audit._compute_hash."""
    for i in range(5):
        log_action(
            user=co_user,
            action_code=f"test.{i}",
            level="L2",
            entity=plant_nis2,
            payload={"i": i},
        )
    logs = AuditLog.objects.filter(entity_type="plant").order_by("timestamp_utc")
    for log in logs:
        assert compute_record_hash(log) == log.record_hash


@pytest.mark.django_db
def test_audit_append_only_trigger(co_user, plant_nis2):
    from django.db import connection

    log = log_action(
        user=co_user,
        action_code="test.create",
        level="L3",
        entity=plant_nis2,
        payload={"x": 1},
    )
    with pytest.raises(Exception, match="append-only"):
        with connection.cursor() as cur:
            cur.execute(
                "UPDATE audit_log SET action_code=%s WHERE id=%s",
                ["tampered", str(log.id)],
            )


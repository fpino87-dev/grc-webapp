import hashlib
import json

import pytest

from core.audit import AuditLog, log_action


@pytest.mark.django_db
def test_hash_chain_valid(co_user, plant_nis2):
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
        expected = hashlib.sha256(
            (json.dumps(log.payload, sort_keys=True, default=str) + log.prev_hash).encode()
        ).hexdigest()
        assert expected == log.record_hash


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


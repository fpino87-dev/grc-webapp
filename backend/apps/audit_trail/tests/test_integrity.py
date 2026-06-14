"""Test del verificatore di integrità: hash per-record + linkage di catena."""
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

User = get_user_model()

URL_VERIFY = "/api/v1/audit-trail/verify-integrity/"


def _plant(code):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code=code, name=code, country="IT", nis2_scope="non_soggetto", status="attivo"
    )


def _craft_log(*, entity_type, prev_hash, record_hash, action_code="forged.event"):
    """Inserisce direttamente un AuditLog (l'INSERT non è bloccato dal trigger,
    solo UPDATE/DELETE lo sono): serve a simulare manomissioni della catena."""
    from core.audit import AuditLog
    return AuditLog.objects.create(
        user_id=uuid.uuid4(),
        user_email_at_time="***@***.it",
        user_role_at_time="",
        action_code=action_code,
        level="L1",
        entity_type=entity_type,
        entity_id=uuid.uuid4(),
        timestamp_utc=timezone.now(),
        payload={},
        prev_hash=prev_hash,
        record_hash=record_hash,
        hash_version="v2",
    )


@pytest.mark.django_db
def test_verify_ok_on_real_chain():
    from core.audit import log_action, verify_audit_integrity
    u = User.objects.create_user(username="iv1", email="iv1@t.it", password="x")
    plant = _plant("IV-OK")
    for i in range(3):
        log_action(user=u, action_code=f"chain.event.{i}", level="L1", entity=plant, payload={"i": i})
    result = verify_audit_integrity()
    assert result["ok"] is True
    assert result["checked"] >= 3


@pytest.mark.django_db
def test_verify_detects_per_record_tamper():
    """record_hash non coerente coi campi → hash_mismatch."""
    from core.audit import verify_audit_integrity
    _craft_log(entity_type="iv_tamper", prev_hash="0" * 64, record_hash="0" * 64)
    result = verify_audit_integrity()
    assert result["ok"] is False
    assert result["error"] == "hash_mismatch"


@pytest.mark.django_db
def test_verify_detects_broken_chain_link():
    """Record self-consistente ma con prev_hash che punta a un predecessore
    inesistente (es. record cancellato a monte) → broken_link."""
    from core.audit import _compute_hash_v2, verify_audit_integrity
    ts = timezone.now()
    uid = uuid.uuid4()
    eid = uuid.uuid4()
    orphan_prev = "a" * 64  # non genesi, non presente nella catena
    rh = _compute_hash_v2(
        user_id=uid, action_code="orphan.event", level="L1",
        entity_type="iv_broken", entity_id=eid, timestamp_utc=ts,
        payload={}, prev_hash=orphan_prev,
    )
    from core.audit import AuditLog
    AuditLog.objects.create(
        user_id=uid, user_email_at_time="***@***.it", user_role_at_time="",
        action_code="orphan.event", level="L1", entity_type="iv_broken",
        entity_id=eid, timestamp_utc=ts, payload={},
        prev_hash=orphan_prev, record_hash=rh, hash_version="v2",
    )
    result = verify_audit_integrity()
    assert result["ok"] is False
    assert result["error"] == "broken_link"
    assert result["entity_type"] == "iv_broken"


@pytest.mark.django_db
def test_verify_endpoint_reports_corruption():
    """L'endpoint UI restituisce status=error quando la catena è compromessa."""
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="ivco", email="ivco@t.it", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    _craft_log(entity_type="iv_api", prev_hash="0" * 64, record_hash="f" * 64)
    c = APIClient()
    c.force_authenticate(user=u)
    resp = c.get(URL_VERIFY)
    assert resp.status_code == 200
    assert resp.data["status"] == "error"

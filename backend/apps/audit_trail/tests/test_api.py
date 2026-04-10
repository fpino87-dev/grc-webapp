"""Test API audit trail e integrità hash chain."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_LOGS = "/api/v1/audit-trail/audit-logs/"
URL_VERIFY = "/api/v1/audit-trail/verify-integrity/"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="aud_user", email="aud@test.com", password="test")


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def audit_entry(db, user):
    from core.audit import log_action
    from apps.plants.models import Plant
    plant = Plant.objects.create(code="AUD-P", name="AuditPlant", country="IT", nis2_scope="non_soggetto", status="attivo")
    log_action(user=user, action_code="test.action", level="L1", entity=plant, payload={"test": True})
    return plant


# ── AuditLog list ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_audit_logs_authenticated(client, audit_entry):
    resp = client.get(URL_LOGS)
    assert resp.status_code == 200
    assert len(resp.data) >= 1


@pytest.mark.django_db
def test_list_audit_logs_unauthenticated():
    resp = APIClient().get(URL_LOGS)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_audit_log_no_write(client, audit_entry):
    """AuditLog è append-only: POST non è permesso."""
    resp = client.post(URL_LOGS, {"action_code": "fake"}, format="json")
    assert resp.status_code in (405, 403)


@pytest.mark.django_db
def test_audit_log_filter_by_action(client, user):
    from core.audit import log_action
    from apps.plants.models import Plant
    plant = Plant.objects.create(code="FLT-P", name="FilterPlant", country="IT", nis2_scope="non_soggetto", status="attivo")
    log_action(user=user, action_code="filter.test.event", level="L2", entity=plant, payload={})
    resp = client.get(f"{URL_LOGS}?action_code=filter.test.event")
    assert resp.status_code == 200


# ── verify-integrity ──────────────────────────────────────────────────────

@pytest.mark.django_db
def test_verify_integrity_endpoint(client, audit_entry):
    resp = client.get(URL_VERIFY)
    assert resp.status_code == 200
    assert "ok" in resp.data or "valid" in resp.data or "verified" in str(resp.data).lower() or "status" in resp.data


# ── core.audit.log_action ─────────────────────────────────────────────────

@pytest.mark.django_db
def test_log_action_creates_entry(user):
    from core.audit import AuditLog
    from core.audit import log_action
    from apps.plants.models import Plant
    plant = Plant.objects.create(code="LA-P", name="LogPlant", country="IT", nis2_scope="non_soggetto", status="attivo")
    before_count = AuditLog.objects.count()
    log_action(user=user, action_code="test.log.create", level="L1", entity=plant, payload={"key": "value"})
    assert AuditLog.objects.count() == before_count + 1


@pytest.mark.django_db
def test_log_action_has_hash(user):
    from core.audit import AuditLog
    from core.audit import log_action
    from apps.plants.models import Plant
    plant = Plant.objects.create(code="HS-P", name="HashPlant", country="IT", nis2_scope="non_soggetto", status="attivo")
    log_action(user=user, action_code="test.hash", level="L2", entity=plant, payload={})
    entry = AuditLog.objects.filter(action_code="test.hash").first()
    assert entry is not None
    assert entry.record_hash != ""
    assert len(entry.record_hash) == 64  # SHA-256 hex


@pytest.mark.django_db
def test_log_action_pseudonymizes_email(user):
    from core.audit import AuditLog
    from core.audit import log_action
    from apps.plants.models import Plant
    plant = Plant.objects.create(code="PS-P", name="PseudoPlant", country="IT", nis2_scope="non_soggetto", status="attivo")
    user.email = "mario.rossi@azienda.it"
    user.save()
    log_action(user=user, action_code="test.pseudo", level="L1", entity=plant, payload={})
    entry = AuditLog.objects.filter(action_code="test.pseudo").first()
    assert entry is not None
    # Email dovrebbe essere mascherata
    assert "mario.rossi@azienda.it" not in entry.user_email_at_time
    assert "***" in entry.user_email_at_time


def test_pseudonymize_email_empty():
    """Riga 16 core/audit.py: email vuota o senza @ ritorna '***'."""
    from core.audit import _pseudonymize_email
    assert _pseudonymize_email("") == "***"
    assert _pseudonymize_email("nodomainsign") == "***"


def test_pseudonymize_email_no_dot_domain():
    """Riga 23 core/audit.py: dominio senza punto (es. localhost)."""
    from core.audit import _pseudonymize_email
    result = _pseudonymize_email("user@localhost")
    assert "***" in result


@pytest.mark.django_db
def test_soft_delete_manager_all_with_deleted():
    """Riga 11 core/models.py: all_with_deleted() include i soft-deleted."""
    from apps.plants.models import Plant
    plant = Plant.objects.create(
        code="DEL-P", name="DeletedPlant", country="IT",
        nis2_scope="non_soggetto", status="attivo"
    )
    plant.soft_delete()
    assert Plant.objects.filter(pk=plant.pk).count() == 0
    assert Plant.objects.all_with_deleted().filter(pk=plant.pk).count() == 1

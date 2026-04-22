"""Test configurazione valutazione fornitori (Fase 1)."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.suppliers.models import SupplierEvaluationConfig

User = get_user_model()

URL_CONFIG = "/api/v1/suppliers/evaluation-config/"


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(username="sup_reg", email="reg@test.com", password="x")


@pytest.fixture
def super_admin_user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="sup_admin", email="admin@test.com", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.SUPER_ADMIN, scope_type="org")
    return u


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


# ── Model ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_get_solo_creates_with_defaults():
    config = SupplierEvaluationConfig.get_solo()
    assert abs(sum(config.weights.values()) - 1.0) < 0.001
    assert set(config.weights.keys()) == {
        "impatto", "accesso", "dati", "dipendenza", "integrazione", "compliance"
    }
    assert config.assessment_validity_months == 12
    assert config.nis2_concentration_bump is True
    assert len(config.parameter_labels["impatto"]["levels"]) == 5


@pytest.mark.django_db
def test_get_solo_is_idempotent():
    a = SupplierEvaluationConfig.get_solo()
    b = SupplierEvaluationConfig.get_solo()
    assert a.pk == b.pk
    assert SupplierEvaluationConfig.objects.count() == 1


@pytest.mark.django_db
def test_classify_uses_thresholds():
    config = SupplierEvaluationConfig.get_solo()
    assert config.classify(1.5) == "basso"
    assert config.classify(2.0) == "medio"
    assert config.classify(2.9) == "medio"
    assert config.classify(3.0) == "alto"
    assert config.classify(3.9) == "alto"
    assert config.classify(4.0) == "critico"
    assert config.classify(5.0) == "critico"


# ── API GET ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_get_config_any_authenticated_user(regular_user):
    resp = _client(regular_user).get(URL_CONFIG)
    assert resp.status_code == 200
    assert "weights" in resp.data
    assert "parameter_labels" in resp.data
    assert "risk_thresholds" in resp.data


@pytest.mark.django_db
def test_get_config_unauthenticated():
    resp = APIClient().get(URL_CONFIG)
    assert resp.status_code in (401, 403)


# ── API PUT permessi ─────────────────────────────────────────────────────

@pytest.mark.django_db
def test_put_config_regular_user_forbidden(regular_user):
    resp = _client(regular_user).put(URL_CONFIG, {"nis2_concentration_bump": False}, format="json")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_put_config_super_admin_ok(super_admin_user):
    resp = _client(super_admin_user).put(URL_CONFIG, {"nis2_concentration_bump": False}, format="json")
    assert resp.status_code == 200
    assert resp.data["nis2_concentration_bump"] is False


# ── API PUT validazione ──────────────────────────────────────────────────

@pytest.mark.django_db
def test_put_weights_sum_must_be_one(super_admin_user):
    bad_weights = {k: 0.10 for k in ["impatto", "accesso", "dati", "dipendenza", "integrazione", "compliance"]}
    resp = _client(super_admin_user).put(URL_CONFIG, {"weights": bad_weights}, format="json")
    assert resp.status_code == 400
    assert "weights" in resp.data


@pytest.mark.django_db
def test_put_weights_missing_key(super_admin_user):
    incomplete = {"impatto": 1.0}
    resp = _client(super_admin_user).put(URL_CONFIG, {"weights": incomplete}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_put_weights_negative(super_admin_user):
    bad = {"impatto": -0.1, "accesso": 0.3, "dati": 0.3, "dipendenza": 0.2, "integrazione": 0.2, "compliance": 0.1}
    resp = _client(super_admin_user).put(URL_CONFIG, {"weights": bad}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_put_parameter_labels_wrong_levels_count(super_admin_user):
    labels = {
        k: {"name": "X", "levels": ["a", "b", "c"]}  # solo 3 invece di 5
        for k in ["impatto", "accesso", "dati", "dipendenza", "integrazione", "compliance"]
    }
    resp = _client(super_admin_user).put(URL_CONFIG, {"parameter_labels": labels}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_put_risk_thresholds_non_monotonic(super_admin_user):
    bad = {"medio": 3.0, "alto": 2.5, "critico": 4.0}
    resp = _client(super_admin_user).put(URL_CONFIG, {"risk_thresholds": bad}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_put_risk_thresholds_out_of_range(super_admin_user):
    bad = {"medio": 0.5, "alto": 3.0, "critico": 6.0}
    resp = _client(super_admin_user).put(URL_CONFIG, {"risk_thresholds": bad}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_put_assessment_validity_out_of_range(super_admin_user):
    resp = _client(super_admin_user).put(URL_CONFIG, {"assessment_validity_months": 0}, format="json")
    assert resp.status_code == 400
    resp = _client(super_admin_user).put(URL_CONFIG, {"assessment_validity_months": 100}, format="json")
    assert resp.status_code == 400


# ── Audit trail ──────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_put_config_creates_audit_log(super_admin_user):
    from core.audit import AuditLog
    count_before = AuditLog.objects.filter(action_code="suppliers.evaluation_config.update").count()
    resp = _client(super_admin_user).put(URL_CONFIG, {"assessment_validity_months": 24}, format="json")
    assert resp.status_code == 200
    count_after = AuditLog.objects.filter(action_code="suppliers.evaluation_config.update").count()
    assert count_after == count_before + 1

"""Test API valutazione interna fornitori + config (Fase 4)."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.suppliers.models import (
    Supplier,
    SupplierEvaluationConfig,
    SupplierInternalEvaluation,
)

User = get_user_model()

URL_SUPPLIERS = "/api/v1/suppliers/suppliers/"
URL_CONFIG = "/api/v1/suppliers/evaluation-config/"


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="ev_api", email="ev_api@test.com", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def super_admin(db):
    from apps.auth_grc.models import UserPlantAccess, GrcRole
    u = User.objects.create_user(username="sa", email="sa@test.com", password="x")
    UserPlantAccess.objects.create(
        user=u,
        role=GrcRole.SUPER_ADMIN,
        scope_type="org",
    )
    return u


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def admin_client(super_admin):
    c = APIClient()
    c.force_authenticate(user=super_admin)
    return c


@pytest.fixture
def supplier(db, user):
    return Supplier.objects.create(
        name="API Co", vat_number="12345678900", created_by=user
    )


# ── Internal evaluation ──────────────────────────────────────────────────

@pytest.mark.django_db
def test_get_current_evaluation_404_when_none(client, supplier):
    resp = client.get(f"{URL_SUPPLIERS}{supplier.id}/internal-evaluation/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_post_create_evaluation(client, supplier):
    payload = {
        "score_impatto": 3,
        "score_accesso": 3,
        "score_dati": 3,
        "score_dipendenza": 3,
        "score_integrazione": 3,
        "score_compliance": 3,
        "notes": "prima",
    }
    resp = client.post(
        f"{URL_SUPPLIERS}{supplier.id}/internal-evaluation/", payload, format="json"
    )
    assert resp.status_code == 201
    assert resp.data["is_current"] is True
    assert resp.data["risk_class"] == "alto"
    assert float(resp.data["weighted_score"]) == 3.0


@pytest.mark.django_db
def test_post_invalid_score_range(client, supplier):
    payload = {k: 6 for k in (
        "score_impatto", "score_accesso", "score_dati",
        "score_dipendenza", "score_integrazione", "score_compliance",
    )}
    resp = client.post(
        f"{URL_SUPPLIERS}{supplier.id}/internal-evaluation/", payload, format="json"
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_get_current_evaluation_after_post(client, supplier):
    payload = {k: 3 for k in (
        "score_impatto", "score_accesso", "score_dati",
        "score_dipendenza", "score_integrazione", "score_compliance",
    )}
    client.post(f"{URL_SUPPLIERS}{supplier.id}/internal-evaluation/", payload, format="json")
    resp = client.get(f"{URL_SUPPLIERS}{supplier.id}/internal-evaluation/")
    assert resp.status_code == 200
    assert resp.data["is_current"] is True


@pytest.mark.django_db
def test_history_endpoint(client, supplier, user):
    from apps.suppliers.services import create_internal_evaluation
    for level in (1, 2, 3):
        create_internal_evaluation(
            supplier,
            {k: level for k in ("impatto", "accesso", "dati", "dipendenza", "integrazione", "compliance")},
            user,
        )
    resp = client.get(f"{URL_SUPPLIERS}{supplier.id}/internal-evaluation/history/")
    assert resp.status_code == 200
    assert resp.data["count"] == 3
    # solo uno is_current=True
    currents = [x for x in resp.data["results"] if x["is_current"]]
    assert len(currents) == 1


@pytest.mark.django_db
def test_evaluation_triggers_risk_adj(client, supplier):
    payload = {k: 5 for k in (
        "score_impatto", "score_accesso", "score_dati",
        "score_dipendenza", "score_integrazione", "score_compliance",
    )}
    client.post(f"{URL_SUPPLIERS}{supplier.id}/internal-evaluation/", payload, format="json")
    supplier.refresh_from_db()
    assert supplier.internal_risk_level == "critico"
    assert supplier.risk_adj == "critico"


# ── Config endpoint ──────────────────────────────────────────────────────

@pytest.mark.django_db
def test_get_config_any_authenticated(client):
    resp = client.get(URL_CONFIG)
    assert resp.status_code == 200
    assert "weights" in resp.data
    assert "risk_thresholds" in resp.data


@pytest.mark.django_db
def test_put_config_forbidden_for_non_admin(client):
    resp = client.put(URL_CONFIG, {"assessment_validity_months": 6}, format="json")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_put_config_allowed_for_super_admin(admin_client):
    resp = admin_client.put(URL_CONFIG, {"assessment_validity_months": 18}, format="json")
    assert resp.status_code == 200
    config = SupplierEvaluationConfig.get_solo()
    assert config.assessment_validity_months == 18


@pytest.mark.django_db
def test_put_config_validates_weights_sum(admin_client):
    bad_weights = {"impatto": 0.5, "accesso": 0.5, "dati": 0.5, "dipendenza": 0.5, "integrazione": 0.5, "compliance": 0.5}
    resp = admin_client.put(URL_CONFIG, {"weights": bad_weights}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_supplier_serializer_exposes_risk_adj(client, supplier):
    resp = client.get(f"{URL_SUPPLIERS}{supplier.id}/")
    assert resp.status_code == 200
    assert "internal_risk_level" in resp.data
    assert "risk_adj" in resp.data
    assert "risk_adj_updated_at" in resp.data

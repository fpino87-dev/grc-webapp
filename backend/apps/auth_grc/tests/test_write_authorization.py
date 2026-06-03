"""P1-3 — Write-authorization SoD: verifica che i ruoli di sola osservazione
(auditor) e i ruoli senza competenza sullo scope NON possano scrivere, mentre i
ruoli operativi/di governance possano.

Nota: DRF valuta `has_permission` PRIMA della validazione del serializer, quindi
un POST con body vuoto restituisce 403 se il permesso nega, 400 se il permesso
passa ma il payload è invalido. Sfruttiamo questa distinzione per testare il
solo livello di autorizzazione senza costruire payload completi.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.auth_grc.models import GrcRole, UserPlantAccess

User = get_user_model()


def client_with_role(role):
    """APIClient autenticato come utente con un dato GrcRole, scope org."""
    safe = role.replace("_", "")
    u = User.objects.create_user(username=f"u_{safe}", email=f"{safe}@test.com", password="x")
    UserPlantAccess.objects.create(user=u, role=role, scope_type="org")
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="SOD-P", name="Plant SoD", country="IT",
        nis2_scope="essenziale", status="attivo",
    )


# ───────────────────────────────────────────────────────────────────────────
# Risk (M06)
# ───────────────────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_auditor_can_read_but_not_create_risk(db):
    auditor = client_with_role(GrcRole.EXTERNAL_AUDITOR)
    assert auditor.get("/api/v1/risk/assessments/").status_code == 200      # lettura ok
    assert auditor.post("/api/v1/risk/assessments/", {}).status_code == 403  # scrittura negata


@pytest.mark.django_db
def test_risk_manager_passes_write_permission(db):
    rm = client_with_role(GrcRole.RISK_MANAGER)
    # passa il permesso (non 403); fallisce semmai la validazione del payload vuoto
    assert rm.post("/api/v1/risk/assessments/", {}).status_code != 403


@pytest.mark.django_db
def test_auditor_cannot_complete_risk(db, plant):
    from apps.risk.models import RiskAssessment
    a = RiskAssessment.objects.create(
        plant=plant, name="R", assessment_type="IT",
        threat_category="malware_ransomware", probability=3, impact=4, status="bozza",
    )
    auditor = client_with_role(GrcRole.INTERNAL_AUDITOR)
    res = auditor.post(f"/api/v1/risk/assessments/{a.id}/complete/")
    assert res.status_code == 403


# ───────────────────────────────────────────────────────────────────────────
# Assets (M04)
# ───────────────────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_auditor_cannot_create_asset(db):
    auditor = client_with_role(GrcRole.EXTERNAL_AUDITOR)
    assert auditor.get("/api/v1/assets/it/").status_code == 200
    assert auditor.post("/api/v1/assets/it/", {}).status_code == 403


@pytest.mark.django_db
def test_control_owner_passes_asset_write(db):
    cow = client_with_role(GrcRole.CONTROL_OWNER)
    assert cow.post("/api/v1/assets/it/", {}).status_code != 403


# ───────────────────────────────────────────────────────────────────────────
# Plants (M01) — config org-level ristretta
# ───────────────────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_plant_manager_cannot_create_business_unit(db):
    pm = client_with_role(GrcRole.PLANT_MANAGER)
    assert pm.get("/api/v1/plants/business-units/").status_code == 200       # lettura ok
    assert pm.post("/api/v1/plants/business-units/", {}).status_code == 403   # config negata


@pytest.mark.django_db
def test_compliance_officer_passes_business_unit_write(db):
    co = client_with_role(GrcRole.COMPLIANCE_OFFICER)
    assert co.post("/api/v1/plants/business-units/", {}).status_code != 403


# ───────────────────────────────────────────────────────────────────────────
# Governance (M00) — assegnazione ruoli sensibile
# ───────────────────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_auditor_cannot_create_role_assignment(db):
    auditor = client_with_role(GrcRole.INTERNAL_AUDITOR)
    assert auditor.get("/api/v1/governance/role-assignments/").status_code == 200
    assert auditor.post("/api/v1/governance/role-assignments/", {}).status_code == 403


@pytest.mark.django_db
def test_risk_manager_cannot_create_role_assignment(db):
    """Anche un ruolo operativo non-governance non assegna ruoli (SoD forte)."""
    rm = client_with_role(GrcRole.RISK_MANAGER)
    assert rm.post("/api/v1/governance/role-assignments/", {}).status_code == 403


# ───────────────────────────────────────────────────────────────────────────
# Tasks (M08)
# ───────────────────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_auditor_cannot_create_task(db):
    auditor = client_with_role(GrcRole.EXTERNAL_AUDITOR)
    assert auditor.get("/api/v1/tasks/tasks/").status_code == 200
    assert auditor.post("/api/v1/tasks/tasks/", {}).status_code == 403


@pytest.mark.django_db
def test_no_role_user_is_forbidden(db):
    """Utente autenticato ma senza alcun UserPlantAccess: niente lettura né scrittura."""
    u = User.objects.create_user(username="norole", email="norole@test.com", password="x")
    c = APIClient()
    c.force_authenticate(user=u)
    assert c.get("/api/v1/risk/assessments/").status_code == 403

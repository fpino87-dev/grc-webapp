"""Test API BIA — processi critici, opzioni trattamento, decisioni rischio."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_PROCESSES = "/api/v1/bia/processes/"
URL_TREATMENTS = "/api/v1/bia/treatment-options/"
URL_DECISIONS = "/api/v1/bia/risk-decisions/"


@pytest.fixture
def user(db):
    """Utente con scope org (vede tutti i processi BIA)."""
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="bia_user", email="bia@test.com", password="test")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="BIA-P", name="Plant BIA", country="IT",
        nis2_scope="essenziale", status="attivo",
    )


@pytest.fixture
def process(db, plant, user):
    from apps.bia.models import CriticalProcess
    return CriticalProcess.objects.create(
        plant=plant,
        name="Produzione assemblaggio",
        criticality=4,
        status="bozza",
        created_by=user,
    )


@pytest.fixture
def treatment(db, process, user):
    from apps.bia.models import TreatmentOption
    return TreatmentOption.objects.create(
        process=process,
        title="Hot standby",
        cost_implementation=50000,
        ale_reduction_pct=70,
        created_by=user,
    )


# ── Processes ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_processes_authenticated(client):
    resp = client.get(URL_PROCESSES)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_list_processes_unauthenticated():
    resp = APIClient().get(URL_PROCESSES)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_create_process(client, plant):
    payload = {
        "plant": str(plant.id),
        "name": "Logistica spedizioni",
        "criticality": 3,
        "status": "bozza",
    }
    resp = client.post(URL_PROCESSES, payload, format="json")
    assert resp.status_code == 201
    assert resp.data["name"] == "Logistica spedizioni"


@pytest.mark.django_db
def test_retrieve_process(client, process):
    resp = client.get(f"{URL_PROCESSES}{process.id}/")
    assert resp.status_code == 200
    assert resp.data["name"] == "Produzione assemblaggio"


@pytest.mark.django_db
def test_update_process(client, process):
    resp = client.patch(f"{URL_PROCESSES}{process.id}/", {"criticality": 5}, format="json")
    assert resp.status_code == 200
    assert resp.data["criticality"] == 5


@pytest.mark.django_db
def test_delete_process(client, process):
    resp = client.delete(f"{URL_PROCESSES}{process.id}/")
    assert resp.status_code == 204


@pytest.mark.django_db
def test_filter_processes_by_plant(client, plant, process):
    resp = client.get(f"{URL_PROCESSES}?plant={plant.id}")
    assert resp.status_code == 200


# ── Treatment options ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_treatments(client):
    resp = client.get(URL_TREATMENTS)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_create_treatment(client, process):
    payload = {
        "process": str(process.id),
        "title": "Warm standby",
        "cost_implementation": 20000,
        "ale_reduction_pct": 50,
    }
    resp = client.post(URL_TREATMENTS, payload, format="json")
    assert resp.status_code == 201
    assert resp.data["title"] == "Warm standby"


@pytest.mark.django_db
def test_retrieve_treatment(client, treatment):
    resp = client.get(f"{URL_TREATMENTS}{treatment.id}/")
    assert resp.status_code == 200
    assert resp.data["title"] == "Hot standby"


@pytest.mark.django_db
def test_update_treatment(client, treatment):
    resp = client.patch(f"{URL_TREATMENTS}{treatment.id}/", {"ale_reduction_pct": 80}, format="json")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_delete_treatment(client, treatment):
    resp = client.delete(f"{URL_TREATMENTS}{treatment.id}/")
    assert resp.status_code == 204


# ── Risk decisions ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_risk_decisions(client):
    resp = client.get(URL_DECISIONS)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_create_risk_decision(client, process, user):
    payload = {
        "process": str(process.id),
        "decision": "accettare",
        "rationale": "Costo di mitigazione superiore al rischio residuo",
        "decided_by": str(user.id),
        "review_by": "2026-12-31",
    }
    resp = client.post(URL_DECISIONS, payload, format="json")
    assert resp.status_code == 201


# ── RBAC plant scoping (S1) ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_plant_manager_does_not_see_process_of_other_plant(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    from apps.bia.models import CriticalProcess
    from apps.plants.models import Plant

    plant_a = Plant.objects.create(
        code="BIA-SC-A", name="A", country="IT",
        nis2_scope="essenziale", status="attivo",
    )
    plant_b = Plant.objects.create(
        code="BIA-SC-B", name="B", country="IT",
        nis2_scope="essenziale", status="attivo",
    )
    CriticalProcess.objects.create(plant=plant_a, name="Proc A", criticality=4, status="bozza")
    CriticalProcess.objects.create(plant=plant_b, name="Proc B", criticality=4, status="bozza")

    pm = User.objects.create_user(username="pm_a_bia", email="pmbia@test", password="x")
    access = UserPlantAccess.objects.create(
        user=pm, role=GrcRole.PLANT_MANAGER, scope_type="single_plant",
    )
    access.scope_plants.set([plant_a])

    c = APIClient()
    c.force_authenticate(user=pm)
    resp = c.get(URL_PROCESSES)
    assert resp.status_code == 200
    names = {item["name"] for item in resp.data["results"]}
    assert names == {"Proc A"}

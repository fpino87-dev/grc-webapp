"""Test API cicli PDCA."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_CYCLES = "/api/v1/pdca/cycles/"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="pdca_user", email="pdca@test.com", password="test")


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="PDCA-P", name="Plant PDCA", country="IT", nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def cycle(db, plant, user):
    from apps.pdca.services import create_cycle
    return create_cycle(plant=plant, title="Ciclo Test", trigger_type="controllo")


# ── CRUD ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_cycles_authenticated(client):
    resp = client.get(URL_CYCLES)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_list_cycles_unauthenticated():
    resp = APIClient().get(URL_CYCLES)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_create_cycle(client, plant):
    payload = {
        "plant": str(plant.id),
        "title": "Ciclo API Test",
        "trigger_type": "controllo",
        "scope_type": "custom",
    }
    resp = client.post(URL_CYCLES, payload, format="json")
    assert resp.status_code == 201
    assert resp.data["title"] == "Ciclo API Test"
    assert resp.data["fase_corrente"] == "plan"


@pytest.mark.django_db
def test_retrieve_cycle(client, cycle):
    resp = client.get(f"{URL_CYCLES}{cycle.id}/")
    assert resp.status_code == 200
    assert resp.data["title"] == "Ciclo Test"


@pytest.mark.django_db
def test_delete_cycle(client, cycle):
    resp = client.delete(f"{URL_CYCLES}{cycle.id}/")
    assert resp.status_code == 204
    # After delete, GET should return 404
    resp2 = client.get(f"{URL_CYCLES}{cycle.id}/")
    assert resp2.status_code == 404


# ── advance action ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_advance_cycle_from_plan_to_do(client, cycle, user):
    assert cycle.fase_corrente == "plan"
    resp = client.post(
        f"{URL_CYCLES}{cycle.id}/advance/",
        {"notes": "Piano completato con tutti i requisiti necessari"},  # >= 20 chars
        format="json",
    )
    assert resp.status_code == 200
    cycle.refresh_from_db()
    assert cycle.fase_corrente == "do"


@pytest.mark.django_db
def test_advance_closed_cycle_returns_error(client, cycle, user):
    cycle.fase_corrente = "chiuso"
    cycle.save()
    resp = client.post(f"{URL_CYCLES}{cycle.id}/advance/", {}, format="json")
    assert resp.status_code in (400, 422)


# ── create_cycle service ──────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_cycle_incident_starts_at_act(plant, user):
    from apps.pdca.services import create_cycle
    cycle = create_cycle(plant=plant, title="Incidente Cycle", trigger_type="incidente")
    assert cycle.fase_corrente == "act"


@pytest.mark.django_db
def test_create_cycle_creates_all_phases(plant, user):
    from apps.pdca.services import create_cycle
    from apps.pdca.models import PdcaPhase
    cycle = create_cycle(plant=plant, title="Full Phases", trigger_type="rischio")
    phases = PdcaPhase.objects.filter(cycle=cycle).values_list("phase", flat=True)
    assert set(phases) == {"plan", "do", "check", "act"}

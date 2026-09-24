"""Cicli PDCA di organizzazione (senza sito): visibili a tutti i siti, creati e
gestiti solo da chi ha accesso a tutta l'organizzazione."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_CYCLES = "/api/v1/pdca/cycles/"
URL_LESSONS = "/api/v1/lessons/lessons/"

PLAN_NOTES = "Piano: aggiornare la procedura di gestione accessi per tutti i siti."


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="ORG-P", name="Plant A", country="IT", nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def co(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="org_co", email="org_co@test.com", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def pm(db, plant):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="org_pm", email="org_pm@test.com", password="x")
    acc = UserPlantAccess.objects.create(user=u, role=GrcRole.PLANT_MANAGER, scope_type="single_plant")
    acc.scope_plants.set([plant])
    return u


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def org_cycle(db):
    from apps.pdca.services import create_cycle
    return create_cycle(plant=None, title="Ciclo di organizzazione", trigger_type="manual", scope_type="org")


@pytest.fixture
def site_cycle(db, plant):
    from apps.pdca.services import create_cycle
    return create_cycle(plant=plant, title="Ciclo del sito", trigger_type="manual")


# ── Creazione ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_org_scope_user_creates_org_cycle(co):
    resp = _client(co).post(URL_CYCLES, {"title": "Awareness phishing", "trigger_type": "manual"}, format="json")
    assert resp.status_code == 201, resp.data
    assert resp.data["plant"] is None
    assert resp.data["plant_name"] is None
    assert resp.data["scope_type"] == "org"
    assert resp.data["can_manage"] is True
    assert len(resp.data["phases"]) == 4


@pytest.mark.django_db
def test_site_user_cannot_create_org_cycle(pm, plant):
    c = _client(pm)
    assert c.post(URL_CYCLES, {"title": "Per tutti", "trigger_type": "manual"}, format="json").status_code == 403
    resp = c.post(URL_CYCLES, {"title": "Mio sito", "trigger_type": "manual", "plant": str(plant.id)}, format="json")
    assert resp.status_code == 201


@pytest.mark.django_db
def test_site_user_cannot_turn_site_cycle_into_org_cycle(pm, co, site_cycle):
    assert _client(pm).patch(f"{URL_CYCLES}{site_cycle.id}/", {"plant": None}, format="json").status_code == 403
    assert _client(co).patch(f"{URL_CYCLES}{site_cycle.id}/", {"plant": None}, format="json").status_code == 200


# ── Visibilità e capacità ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_site_user_sees_org_cycles_read_only(pm, org_cycle, site_cycle):
    rows = {r["title"]: r for r in _client(pm).get(URL_CYCLES).data["results"]}
    assert set(rows) == {"Ciclo di organizzazione", "Ciclo del sito"}
    assert rows["Ciclo di organizzazione"]["can_manage"] is False
    assert rows["Ciclo del sito"]["can_manage"] is True


@pytest.mark.django_db
def test_org_filter(co, org_cycle, site_cycle):
    rows = _client(co).get(URL_CYCLES, {"org": "true"}).data["results"]
    assert [r["title"] for r in rows] == ["Ciclo di organizzazione"]


@pytest.mark.django_db
def test_capabilities(co, pm):
    assert _client(co).get(f"{URL_CYCLES}capabilities/").data == {"can_manage_org": True}
    assert _client(pm).get(f"{URL_CYCLES}capabilities/").data == {"can_manage_org": False}


# ── Workflow ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_site_user_cannot_drive_org_cycle(pm, org_cycle, site_cycle):
    c = _client(pm)
    base = f"{URL_CYCLES}{org_cycle.id}/"
    assert c.post(f"{base}advance/", {"notes": PLAN_NOTES}, format="json").status_code == 403
    assert c.post(f"{base}archivia/", {"motivo": "Non più necessario per nessun sito."}, format="json").status_code == 403
    assert c.patch(base, {"title": "x"}, format="json").status_code == 403
    assert c.delete(base, {"reason": "Creato per errore."}, format="json").status_code == 403
    # sul ciclo del proprio sito invece sì
    assert c.post(f"{URL_CYCLES}{site_cycle.id}/advance/", {"notes": PLAN_NOTES}, format="json").status_code == 200


@pytest.mark.django_db
def test_org_cycle_full_workflow_creates_org_lesson(co, org_cycle):
    from apps.documents.models import Evidence
    from apps.lessons.models import LessonLearned

    c = _client(co)
    base = f"{URL_CYCLES}{org_cycle.id}/"
    ev = Evidence.objects.create(title="Verbale formazione", plant=None, created_by=co)
    assert c.post(f"{base}advance/", {"notes": PLAN_NOTES}, format="json").status_code == 200
    assert c.post(f"{base}advance/", {"evidence_id": str(ev.id)}, format="json").status_code == 200
    assert c.post(f"{base}advance/", {"notes": "Verifica eseguita su tutti i siti.", "outcome": "ok"},
                  format="json").status_code == 200
    resp = c.post(f"{base}close/", {"act_description": "Procedura standardizzata e pubblicata per tutti."},
                  format="json")
    assert resp.status_code == 200, resp.data
    lesson = LessonLearned.objects.get(source_id=org_cycle.id)
    assert lesson.plant_id is None


@pytest.mark.django_db
def test_org_cycle_ko_recycle_stays_org(co, org_cycle):
    from apps.documents.models import Evidence
    from apps.pdca.models import PdcaCycle

    c = _client(co)
    base = f"{URL_CYCLES}{org_cycle.id}/"
    ev = Evidence.objects.create(title="Evidenza", plant=None, created_by=co)
    c.post(f"{base}advance/", {"notes": PLAN_NOTES}, format="json")
    c.post(f"{base}advance/", {"evidence_id": str(ev.id)}, format="json")
    c.post(f"{base}advance/", {"notes": "Verifica non superata.", "outcome": "ko"}, format="json")
    org_cycle.refresh_from_db()
    assert PdcaCycle.objects.get(pk=org_cycle.reopened_as_id).plant_id is None


# ── Lesson Learned di organizzazione ────────────────────────────────────────

@pytest.fixture
def org_lesson(db):
    from apps.lessons.models import LessonLearned
    return LessonLearned.objects.create(title="Lesson org", description="Valida per tutti", plant=None)


@pytest.mark.django_db
def test_site_user_sees_org_lesson_but_cannot_change_it(pm, org_lesson):
    c = _client(pm)
    titles = [r["title"] for r in c.get(URL_LESSONS).data["results"]]
    assert "Lesson org" in titles
    assert c.post(f"{URL_LESSONS}{org_lesson.id}/validate/").status_code == 403
    assert c.patch(f"{URL_LESSONS}{org_lesson.id}/", {"title": "x"}, format="json").status_code == 403
    assert c.post(URL_LESSONS, {"title": "Nuova", "description": "d"}, format="json").status_code == 403


@pytest.mark.django_db
def test_org_user_manages_org_lesson(co, org_lesson):
    c = _client(co)
    assert c.post(f"{URL_LESSONS}{org_lesson.id}/validate/").status_code == 200
    resp = c.post(URL_LESSONS, {"title": "Nuova org", "description": "d"}, format="json")
    assert resp.status_code == 201 and resp.data["plant"] is None


@pytest.mark.django_db
def test_site_filter_includes_org_cycles(co, plant, org_cycle, site_cycle):
    from apps.pdca.services import create_cycle
    from apps.plants.models import Plant
    other = Plant.objects.create(code="ORG-B", name="Plant B", country="IT", nis2_scope="non_soggetto", status="attivo")
    create_cycle(plant=other, title="Altro sito", trigger_type="manual")
    c = _client(co)
    titles = {r["title"] for r in c.get(URL_CYCLES, {"site": str(plant.id)}).data["results"]}
    assert titles == {"Ciclo di organizzazione", "Ciclo del sito"}
    exact = {r["title"] for r in c.get(URL_CYCLES, {"plant": str(plant.id)}).data["results"]}
    assert exact == {"Ciclo del sito"}
    assert c.get(URL_CYCLES, {"site": "non-uuid"}).data["results"] == []

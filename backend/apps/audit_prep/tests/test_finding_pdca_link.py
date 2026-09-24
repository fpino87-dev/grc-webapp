"""Collegamento univoco finding ↔ PDCA (dal finding e dal menù PDCA) e
chiusura del finding coerente con lo stato del PDCA."""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

User = get_user_model()

URL_FINDINGS = "/api/v1/audit-prep/findings/"
URL_CYCLES = "/api/v1/pdca/cycles/"
PLAN = "Piano: aggiornare la procedura e formare il personale coinvolto."


def _plant(code):
    from apps.plants.models import Plant
    return Plant.objects.create(code=code, name=code, country="IT", nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def plant(db):
    return _plant("LK-A")


@pytest.fixture
def other_plant(db):
    return _plant("LK-B")


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="lk_co", email="lk_co@test.com", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _prep(plant, title="Audit cliente", audit_type="seconda_parte"):
    from apps.audit_prep.models import AuditPrep
    return AuditPrep.objects.create(plant=plant, title=title, audit_type=audit_type, requesting_party="OEM Alfa")


def _finding(prep, user, ftype="observation", title="Osservazione"):
    from apps.audit_prep.services import open_finding
    return open_finding(prep, ftype, title, "descrizione", timezone.localdate(), user)


def _cycle(plant, title="Ciclo"):
    from apps.pdca.services import create_cycle
    return create_cycle(plant=plant, title=title, trigger_type="manual")


def _to_act(cycle, user):
    from apps.documents.models import Evidence
    from apps.pdca.services import advance_phase
    ev = Evidence.objects.create(title="ev", plant=cycle.plant, created_by=user)
    advance_phase(cycle, user, phase_notes=PLAN)
    advance_phase(cycle, user, evidence=ev)
    advance_phase(cycle, user, phase_notes="Verifica eseguita con esito positivo.", outcome="ok")
    cycle.refresh_from_db()
    return cycle


# ── Dal finding ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_open_pdca_from_observation(client, plant, user):
    f = _finding(_prep(plant), user)
    assert f.pdca_cycle_id is None
    resp = client.post(f"{URL_FINDINGS}{f.id}/open-pdca/", {}, format="json")
    assert resp.status_code == 201, resp.data
    f.refresh_from_db()
    cycle = f.pdca_cycle
    assert cycle.plant_id == plant.id
    assert cycle.trigger_type == "finding_observation"
    assert cycle.audit_subtype == "seconda_parte"
    assert cycle.title == "[OBSERVATION] Osservazione"
    assert resp.data["pdca_phase"] == "plan"
    # un secondo PDCA per lo stesso finding non si apre
    assert client.post(f"{URL_FINDINGS}{f.id}/open-pdca/", {}, format="json").status_code == 400


@pytest.mark.django_db
def test_link_existing_pdca_rules(client, plant, other_plant, user):
    prep = _prep(plant)
    f1, f2 = _finding(prep, user, title="Oss 1"), _finding(prep, user, title="Oss 2")
    cycle = _cycle(plant)
    assert client.post(f"{URL_FINDINGS}{f1.id}/link-pdca/", {"pdca_cycle": str(cycle.id)}, format="json").status_code == 200
    # opzione A: stesso PDCA per un altro finding dello stesso audit
    assert client.post(f"{URL_FINDINGS}{f2.id}/link-pdca/", {"pdca_cycle": str(cycle.id)}, format="json").status_code == 200
    # ma non per un finding di un altro audit
    f3 = _finding(_prep(plant, "Altro audit"), user, title="Oss 3")
    resp = client.post(f"{URL_FINDINGS}{f3.id}/link-pdca/", {"pdca_cycle": str(cycle.id)}, format="json")
    assert resp.status_code == 400 and "Audit cliente" in resp.data["error"]
    # né a un PDCA di un altro sito
    resp = client.post(f"{URL_FINDINGS}{f3.id}/link-pdca/", {"pdca_cycle": str(_cycle(other_plant).id)}, format="json")
    assert resp.status_code == 400
    cycle.refresh_from_db()
    assert cycle.audit_subtype == "seconda_parte"


@pytest.mark.django_db
def test_unlink_requires_reason(client, plant, user):
    f = _finding(_prep(plant), user)
    cycle = _cycle(plant)
    client.post(f"{URL_FINDINGS}{f.id}/link-pdca/", {"pdca_cycle": str(cycle.id)}, format="json")
    assert client.post(f"{URL_FINDINGS}{f.id}/unlink-pdca/", {"reason": "no"}, format="json").status_code == 400
    resp = client.post(f"{URL_FINDINGS}{f.id}/unlink-pdca/", {"reason": "Collegato al ciclo sbagliato"}, format="json")
    assert resp.status_code == 200 and resp.data["pdca_cycle"] is None


@pytest.mark.django_db
def test_without_pdca_filter(client, plant, user):
    prep = _prep(plant)
    _finding(prep, user, "minor_nc", "NC con PDCA")
    _finding(prep, user, "observation", "Oss senza PDCA")
    rows = client.get(URL_FINDINGS, {"audit_prep": str(prep.id), "without_pdca": "true"}).data["results"]
    assert [r["title"] for r in rows] == ["Oss senza PDCA"]


# ── Dal menù PDCA ───────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_pdca_from_finding_in_pdca_menu(client, plant, other_plant, user):
    f = _finding(_prep(plant), user)
    resp = client.post(URL_CYCLES, {
        "title": "Rivedere la classificazione", "trigger_type": "audit", "plant": str(other_plant.id),
        "finding": str(f.id),
    }, format="json")
    assert resp.status_code == 201, resp.data
    assert str(resp.data["plant"]) == str(plant.id)  # sito dal finding, non dal form
    assert resp.data["trigger_type"] == "finding_observation"
    assert resp.data["audit_subtype"] == "seconda_parte"
    assert [x["id"] for x in resp.data["findings"]] == [str(f.id)]
    assert resp.data["findings"][0]["requesting_party"] == "OEM Alfa"
    f.refresh_from_db()
    assert str(f.pdca_cycle_id) == str(resp.data["id"])


@pytest.mark.django_db
def test_link_and_unlink_from_pdca_menu(client, plant, user):
    f = _finding(_prep(plant), user)
    cycle = _cycle(plant)
    resp = client.post(f"{URL_CYCLES}{cycle.id}/link-finding/", {"finding": str(f.id)}, format="json")
    assert resp.status_code == 200 and len(resp.data["findings"]) == 1
    resp = client.post(f"{URL_CYCLES}{cycle.id}/unlink-finding/",
                       {"finding": str(f.id), "reason": "Collegamento errato"}, format="json")
    assert resp.status_code == 200 and resp.data["findings"] == []


@pytest.mark.django_db
def test_open_cycles_filter(client, plant, user):
    open_c = _cycle(plant, "Aperto")
    closed = _cycle(plant, "Archiviato")
    from apps.pdca.services import archivia_cycle
    archivia_cycle(closed, user, "Non più necessario per questo sito.")
    rows = client.get(URL_CYCLES, {"plant": str(plant.id), "open": "true"}).data["results"]
    assert [r["id"] for r in rows] == [str(open_c.id)]


@pytest.mark.django_db
def test_site_user_cannot_link_finding_of_other_site(plant, other_plant, user):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    pm = User.objects.create_user(username="lk_pm", email="lk_pm@test.com", password="x")
    acc = UserPlantAccess.objects.create(user=pm, role=GrcRole.PLANT_MANAGER, scope_type="single_plant")
    acc.scope_plants.set([other_plant])
    f = _finding(_prep(plant), user)
    cycle = _cycle(other_plant)
    c = APIClient()
    c.force_authenticate(user=pm)
    assert c.post(f"{URL_CYCLES}{cycle.id}/link-finding/", {"finding": str(f.id)}, format="json").status_code == 404


# ── Chiusura del finding ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_close_nc_with_pdca_in_plan_is_rejected_without_side_effects(client, plant, user):
    from apps.documents.models import Evidence
    f = _finding(_prep(plant), user, "minor_nc", "NC")
    ev = Evidence.objects.create(title="e", plant=plant, created_by=user)
    resp = client.post(f"{URL_FINDINGS}{f.id}/close/", {"closure_notes": "x" * 30, "evidence_id": str(ev.id)}, format="json")
    assert resp.status_code == 400
    assert "PLAN" in resp.data["error"]
    f.refresh_from_db()
    assert f.status == "open" and f.lesson_learned_id is None


@pytest.mark.django_db
def test_close_nc_with_pdca_in_act_closes_both(client, plant, user):
    from apps.documents.models import Evidence
    f = _finding(_prep(plant), user, "minor_nc", "NC")
    _to_act(f.pdca_cycle, user)
    ev = Evidence.objects.create(title="e", plant=plant, created_by=user)
    notes = "Procedura aggiornata e diffusa a tutto il personale."
    resp = client.post(f"{URL_FINDINGS}{f.id}/close/", {"closure_notes": notes, "evidence_id": str(ev.id)}, format="json")
    assert resp.status_code == 200, resp.data
    f.refresh_from_db()
    assert f.status == "closed"
    assert f.pdca_cycle.fase_corrente == "chiuso"
    assert f.pdca_cycle.act_description == notes


@pytest.mark.django_db
def test_shared_pdca_in_act_needs_to_be_closed_first(client, plant, user):
    prep = _prep(plant)
    f1, f2 = _finding(prep, user, title="Oss 1"), _finding(prep, user, title="Oss 2")
    cycle = _cycle(plant)
    for f in (f1, f2):
        client.post(f"{URL_FINDINGS}{f.id}/link-pdca/", {"pdca_cycle": str(cycle.id)}, format="json")
    _to_act(cycle, user)
    resp = client.post(f"{URL_FINDINGS}{f1.id}/close/", {"closure_notes": "x" * 30}, format="json")
    assert resp.status_code == 400
    from apps.pdca.services import close_cycle
    close_cycle(cycle, user, act_description="Azione comune standardizzata per entrambe.")
    f1.refresh_from_db()
    assert f1.status == "in_response"  # il PDCA chiuso porta i finding collegati in risposta
    assert client.post(f"{URL_FINDINGS}{f1.id}/close/", {"closure_notes": "chiusa"}, format="json").status_code == 200


@pytest.mark.django_db
def test_observation_without_pdca_closes_freely(client, plant, user):
    f = _finding(_prep(plant), user)
    assert client.post(f"{URL_FINDINGS}{f.id}/close/", {"closure_notes": ""}, format="json").status_code == 200

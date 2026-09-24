"""Ordine del giorno §9.3.2, chiusura, decisioni con task/PDCA collegati."""
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.management_review.models import ReviewAction, ReviewAgendaItem

User = get_user_model()
pytestmark = pytest.mark.django_db

URL_REVIEWS = "/api/v1/management-review/reviews/"
URL_ITEMS = "/api/v1/management-review/agenda-items/"
URL_ACTIONS = "/api/v1/management-review/review-actions/"


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="mr_ag", email="ag@test.com", password="x", first_name="Carla", last_name="Neri")
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
    return Plant.objects.create(code="AG-P", name="Plant AG", country="IT", nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def review(client, plant):
    resp = client.post(URL_REVIEWS, {"plant": str(plant.id), "title": "Riesame 2026",
                                     "review_date": "2026-03-10"}, format="json")
    assert resp.status_code == 201
    return resp.data


def _items(review):
    return {i["code"]: i for i in review["agenda_items"]}


def test_complete_requires_mandatory_agenda_items(client, review):
    resp = client.post(f"{URL_REVIEWS}{review['id']}/start/")
    assert resp.status_code == 200 and resp.data["status"] == "in_corso"

    resp = client.post(f"{URL_REVIEWS}{review['id']}/complete/")
    assert resp.status_code == 400
    assert resp.data["code"] == "agenda_incomplete"
    assert len(resp.data["missing"]) == 7

    items = _items(review)
    for code, item in items.items():
        if code == "rischi":
            continue
        assert client.patch(f"{URL_ITEMS}{item['id']}/", {"discussion": f"Discusso {code}"}, format="json").status_code == 200
    # il punto "rischi" è coperto da una decisione invece che da una discussione
    resp = client.post(URL_ACTIONS, {"review": review["id"], "agenda_item": items["rischi"]["id"],
                                     "description": "Rivedere il piano di trattamento"}, format="json")
    assert resp.status_code == 201, resp.data

    resp = client.post(f"{URL_REVIEWS}{review['id']}/complete/")
    assert resp.status_code == 200, resp.data
    assert resp.data["status"] == "completato"
    # prossimo riesame proposto dalla policy (default annuale)
    assert resp.data["next_review_date"] == "2027-03-10"


def test_custom_agenda_items_and_mandatory_protection(client, review):
    resp = client.post(URL_ITEMS, {"review": review["id"], "title": "Budget sicurezza 2027"}, format="json")
    assert resp.status_code == 201
    custom_id = resp.data["id"]
    assert resp.data["code"] == "custom" and resp.data["mandatory"] is False

    mandatory = _items(review)["contesto"]["id"]
    assert client.delete(f"{URL_ITEMS}{mandatory}/").status_code == 400
    assert client.delete(f"{URL_ITEMS}{custom_id}/").status_code == 204
    assert not ReviewAgendaItem.objects.filter(pk=custom_id).exists()  # soft delete


def test_decision_creates_task_for_role_and_pdca(client, review, plant):
    item = _items(review)["miglioramento"]
    due = (timezone.localdate() + datetime.timedelta(days=60)).isoformat()
    resp = client.post(URL_ACTIONS, {
        "review": review["id"], "agenda_item": item["id"], "decision_type": "modifica_sgsi",
        "description": "Introdurre MFA sugli accessi remoti OT\nDettagli…", "due_date": due,
        "create_task": True, "task_role": "compliance_officer", "create_pdca": True,
    }, format="json")
    assert resp.status_code == 201, resp.data
    action = ReviewAction.objects.select_related("task", "pdca_cycle").get(pk=resp.data["id"])
    assert action.task.assigned_role == "compliance_officer"
    assert action.task.assigned_to is None  # mai a un utente diretto
    assert action.task.source_module == "M13" and action.task.priority == "alta"
    assert action.task.plant_id == plant.id
    assert action.pdca_cycle.trigger_type == "management_review"
    assert action.pdca_cycle.title == "Introdurre MFA sugli accessi remoti OT"
    assert resp.data["task_status"] == "aperto" and resp.data["pdca_phase"] == "plan"


def test_decision_task_requires_role_and_due_date(client, review):
    base = {"review": review["id"], "description": "x", "create_task": True}
    resp = client.post(URL_ACTIONS, {**base, "task_role": "compliance_officer"}, format="json")
    assert resp.status_code == 400
    resp = client.post(URL_ACTIONS, {**base, "due_date": "2026-12-01"}, format="json")
    assert resp.status_code == 400
    # rollback: nessuna decisione orfana
    assert not ReviewAction.objects.filter(review_id=review["id"]).exists()


def test_org_review_pdca_is_org_wide_or_on_chosen_site(client, plant):
    resp = client.post(URL_REVIEWS, {"title": "Riesame org", "review_date": "2026-03-10"}, format="json")
    rid = resp.data["id"]
    base = {"review": rid, "description": "Programma awareness", "create_pdca": True}
    # Senza sito → PDCA di organizzazione
    resp = client.post(URL_ACTIONS, base, format="json")
    assert resp.status_code == 201, resp.data
    cycle = ReviewAction.objects.get(pk=resp.data["id"]).pdca_cycle
    assert cycle.plant_id is None
    # Con sito indicato → PDCA di quel sito
    resp = client.post(URL_ACTIONS, {**base, "pdca_plant": str(plant.id)}, format="json")
    assert resp.status_code == 201, resp.data
    assert ReviewAction.objects.get(pk=resp.data["id"]).pdca_cycle.plant_id == plant.id


def test_minutes_locked_after_approval(client, review, user):
    from apps.management_review.models import ManagementReview

    item = _items(review)["contesto"]
    action = client.post(URL_ACTIONS, {"review": review["id"], "description": "Azione"}, format="json").data
    ManagementReview.objects.filter(pk=review["id"]).update(approval_status="approvato", status="completato")

    assert client.patch(f"{URL_ITEMS}{item['id']}/", {"discussion": "modifica"}, format="json").status_code == 400
    assert client.post(URL_ITEMS, {"review": review["id"], "title": "Nuovo"}, format="json").status_code == 400
    assert client.post(URL_ACTIONS, {"review": review["id"], "description": "Nuova"}, format="json").status_code == 400
    assert client.patch(f"{URL_ACTIONS}{action['id']}/", {"description": "cambiata"}, format="json").status_code == 400
    assert client.delete(f"{URL_ACTIONS}{action['id']}/").status_code == 400
    assert client.patch(f"{URL_REVIEWS}{review['id']}/", {"next_review_date": "2028-01-01"}, format="json").status_code == 400
    assert client.post(f"{URL_REVIEWS}{review['id']}/summary/", {"text": "x"}, format="json").status_code == 400
    # l'avanzamento delle azioni resta aggiornabile
    resp = client.patch(f"{URL_ACTIONS}{action['id']}/", {"status": "chiuso"}, format="json")
    assert resp.status_code == 200 and resp.data["closed_at"]


def test_approve_requires_completed_meeting(client, review):
    from apps.management_review.models import ManagementReview

    ManagementReview.objects.filter(pk=review["id"]).update(snapshot_generated_at=timezone.now())
    resp = client.post(f"{URL_REVIEWS}{review['id']}/approve/", {"note": "ok"}, format="json")
    assert resp.status_code == 400

"""Valutazione dei rischi approvata dall'organo nel riesame (procedura di
risk management §5): elenco delle valutazioni in approvazione per
perimetro, punto all'ordine del giorno, esito obbligatorio alla chiusura,
applicazione al registro all'approvazione del verbale."""
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.risk import services as risk_services
from apps.risk.tests.test_register import _plant, _user

pytestmark = pytest.mark.django_db

URL = "/api/v1/management-review/reviews/"
ITEMS = "/api/v1/management-review/agenda-items/"


def _api(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def co(db):
    return _user("mr_cyc_co", role="compliance_officer")


@pytest.fixture
def plant(db):
    return _plant("RC-1")


@pytest.fixture
def body(db):
    from apps.governance.models import SecurityCommittee
    return SecurityCommittee.objects.create(name="CdA", committee_type="cda")


def _submitted(plant):
    from apps.risk.models import RiskAssessmentCycle
    return RiskAssessmentCycle.objects.create(
        plant=plant, kind="primo", status="in_approvazione", started_at=timezone.now())


def _review(co, plant, kind, body=None):
    from apps.management_review.models import ManagementReview
    r = _api(co).post(URL, {"title": f"Riesame {kind}", "review_date": str(timezone.localdate()),
                            "plant": str(plant.pk) if plant else None, "kind": kind}, format="json")
    assert r.status_code == 201, r.data
    if body is not None:
        ManagementReview.objects.filter(pk=r.data["id"]).update(governing_body=body)
    return r.data["id"]


def _add(co, rid, cycle):
    r = _api(co).post(f"{URL}{rid}/risk-cycle-items/", {"cycle_ids": [str(cycle.pk)]}, format="json")
    assert r.status_code == 200, r.data
    return r.data


def _item(rid, cycle):
    from apps.management_review.models import ReviewAgendaItem
    return ReviewAgendaItem.objects.get(review_id=rid, risk_cycle=cycle, deleted_at__isnull=True)


def _close_and_approve(co, rid):
    from apps.management_review.models import ManagementReview, ReviewAgendaItem
    ReviewAgendaItem.objects.filter(review_id=rid, mandatory=True).update(discussion="Esaminato")
    r = _api(co).post(f"{URL}{rid}/complete/")
    assert r.status_code == 200, r.data
    ManagementReview.objects.filter(pk=rid).update(
        snapshot_generated_at=timezone.now(), snapshot_data={"generated_at": timezone.now().isoformat()})
    r = _api(co).post(f"{URL}{rid}/approve/", {}, format="json")
    assert r.status_code == 200, r.data


def test_full_review_approves_register(co, plant, body):
    cycle = _submitted(plant)
    rid = _review(co, plant, "completo", body)

    rows = _api(co).get(f"{URL}{rid}/pending-risk-cycles/").data
    assert [r["id"] for r in rows] == [str(cycle.pk)] and rows[0]["selected"] is False
    data = _add(co, rid, cycle)
    assert len(data["added"]) == 1
    info = next(i for i in data["review"]["agenda_items"] if i["code"] == "risk_cycle")["risk_cycle_info"]
    assert info["status"] == "in_approvazione" and info["plant_code"] == "RC-1"

    # senza esito la riunione non si chiude
    from apps.management_review.models import ReviewAgendaItem
    ReviewAgendaItem.objects.filter(review_id=rid, mandatory=True).update(discussion="Esaminato")
    assert _api(co).post(f"{URL}{rid}/complete/").status_code == 400

    item = _item(rid, cycle)
    r = _api(co).patch(f"{ITEMS}{item.pk}/", {"document_outcome": "approvato"}, format="json")
    assert r.status_code == 200, r.data
    _close_and_approve(co, rid)

    cycle.refresh_from_db()
    item.refresh_from_db()
    assert cycle.status == "approvato" and cycle.approved_by_body == body and str(cycle.approval_review_id) == rid
    assert cycle.snapshot is not None and item.document_outcome_applied_at is not None
    assert risk_services.approved_cycle(plant) == cycle

    from apps.management_review.models import ManagementReview
    from apps.management_review.report import build_report
    doc = build_report(ManagementReview.objects.get(pk=rid))
    assert any(s["heading"] == "Valutazioni dei rischi deliberate" for s in doc["sections"])


def test_approval_needs_governing_body(co, plant):
    cycle = _submitted(plant)
    rid = _review(co, plant, "mirato")
    _add(co, rid, cycle)
    r = _api(co).patch(f"{ITEMS}{_item(rid, cycle).pk}/", {"document_outcome": "approvato"}, format="json")
    assert r.status_code == 400


def test_targeted_review_rejects_back_to_evaluation(co, plant):
    cycle = _submitted(plant)
    rid = _review(co, plant, "mirato")
    _add(co, rid, cycle)
    _api(co).patch(f"{ITEMS}{_item(rid, cycle).pk}/",
                   {"document_outcome": "respinto", "discussion": "Piano di trattamento insufficiente"},
                   format="json")
    _close_and_approve(co, rid)
    cycle.refresh_from_db()
    assert cycle.status == "in_corso" and cycle.approved_at is None


def test_postponed_stays_in_approval_and_one_review_at_a_time(co, plant):
    cycle = _submitted(plant)
    first = _review(co, plant, "mirato")
    _add(co, first, cycle)
    second = _review(co, plant, "mirato")
    assert _api(co).get(f"{URL}{second}/pending-risk-cycles/").data == []

    _api(co).patch(f"{ITEMS}{_item(first, cycle).pk}/", {"document_outcome": "rinviato"}, format="json")
    _close_and_approve(co, first)
    cycle.refresh_from_db()
    assert cycle.status == "in_approvazione"
    assert [r["id"] for r in _api(co).get(f"{URL}{second}/pending-risk-cycles/").data] == [str(cycle.pk)]


def test_group_and_centralized_only_in_org_review(co, plant):
    group = _submitted(None)
    site = _submitted(plant)
    site_review = _review(co, plant, "mirato")
    org_review = _review(co, None, "mirato")
    assert [r["id"] for r in _api(co).get(f"{URL}{site_review}/pending-risk-cycles/").data] == [str(site.pk)]
    assert {r["id"] for r in _api(co).get(f"{URL}{org_review}/pending-risk-cycles/").data} == {
        str(group.pk), str(site.pk)}

    risk_services.save_governance_policy(co, None, {"preset": "centralizzato"})
    assert _api(co).get(f"{URL}{site_review}/pending-risk-cycles/").data == []


def test_returned_from_risk_after_session_is_not_applied(co, plant, body):
    cycle = _submitted(plant)
    rid = _review(co, plant, "mirato", body)
    _add(co, rid, cycle)
    item = _item(rid, cycle)
    _api(co).patch(f"{ITEMS}{item.pk}/", {"document_outcome": "approvato"}, format="json")
    risk_services.return_cycle(co, cycle, "Manca un rischio")
    _close_and_approve(co, rid)
    item.refresh_from_db()
    cycle.refresh_from_db()
    assert cycle.status == "in_corso" and item.document_outcome_applied_at is None
    assert item.document_outcome_error

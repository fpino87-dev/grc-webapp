"""Accettazioni del rischio deliberate dall'organo nel riesame (procedura di
risk management §10): elenco in attesa per perimetro, punti all'ordine del
giorno nel riesame completo e mirato, esito obbligatorio alla chiusura,
applicazione all'approvazione del verbale."""
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.risk import services as risk_services
from apps.risk.tests.test_register import _completed_risk, _plant, _user, threats  # noqa: F401

pytestmark = pytest.mark.django_db

URL = "/api/v1/management-review/reviews/"
ITEMS = "/api/v1/management-review/agenda-items/"


def _api(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def co(db):
    return _user("mr_co", role="compliance_officer")


@pytest.fixture
def plant(db):
    return _plant("RA-1")


def _self_managed_acceptance(user, plant, threat):
    """Rischio valutato e trattato dal suo owner: l'accettazione attende l'organo."""
    from apps.risk.models import RiskAssessmentCycle

    if not RiskAssessmentCycle.objects.filter(plant=plant).exists():
        risk_services.start_cycle(user, plant, "primo")
    asset_type = threat.asset_types[0]
    risk = _completed_risk(user, plant, threat, probability=2, impact_operational=3, treatment="accettare",
                           expected_probability=None, expected_impact=None, asset_type=asset_type)
    acc = risk_services.request_acceptance(user, risk, rationale="Costo della misura sproporzionato")
    assert acc.status == "pending" and acc.requires_body
    return acc


def _review(co, plant, kind):
    r = _api(co).post(URL, {"title": f"Riesame {kind}", "review_date": str(timezone.localdate()),
                            "plant": str(plant.pk) if plant else None, "kind": kind}, format="json")
    assert r.status_code == 201, r.data
    return r.data["id"]


def _add(co, rid, acc):
    r = _api(co).post(f"{URL}{rid}/acceptance-items/", {"acceptance_ids": [str(acc.pk)]}, format="json")
    assert r.status_code == 200, r.data
    return r.data


def _item(rid, acc):
    from apps.management_review.models import ReviewAgendaItem
    return ReviewAgendaItem.objects.get(review_id=rid, risk_acceptance=acc, deleted_at__isnull=True)


def _close_and_approve(co, rid, **approve):
    from apps.management_review.models import ManagementReview, ReviewAgendaItem
    ReviewAgendaItem.objects.filter(review_id=rid, mandatory=True).update(discussion="Esaminato")
    r = _api(co).post(f"{URL}{rid}/complete/")
    assert r.status_code == 200, r.data
    ManagementReview.objects.filter(pk=rid).update(
        snapshot_generated_at=timezone.now(), snapshot_data={"generated_at": timezone.now().isoformat()})
    r = _api(co).post(f"{URL}{rid}/approve/", approve, format="json")
    assert r.status_code == 200, r.data


def test_full_review_decides_self_managed_acceptance(co, plant, threats):  # noqa: F811
    acc = _self_managed_acceptance(co, plant, threats["malware"])
    rid = _review(co, plant, "completo")

    rows = _api(co).get(f"{URL}{rid}/pending-acceptances/").data
    assert [r["id"] for r in rows] == [str(acc.pk)] and rows[0]["selected"] is False
    data = _add(co, rid, acc)
    assert len(data["added"]) == 1
    assert _api(co).get(f"{URL}{rid}/pending-acceptances/").data[0]["selected"] is True
    info = next(i for i in data["review"]["agenda_items"] if i["code"] == "risk_acceptance")["risk_acceptance_info"]
    assert info["risk_class"] == acc.risk_class and info["status"] == "pending"

    # senza esito la riunione non si chiude
    from apps.management_review.models import ReviewAgendaItem
    ReviewAgendaItem.objects.filter(review_id=rid, mandatory=True).update(discussion="Esaminato")
    r = _api(co).post(f"{URL}{rid}/complete/")
    assert r.status_code == 400

    item = _item(rid, acc)
    r = _api(co).patch(f"{ITEMS}{item.pk}/", {"document_outcome": "approvato"}, format="json")
    assert r.status_code == 200, r.data
    _close_and_approve(co, rid)

    acc.refresh_from_db()
    item.refresh_from_db()
    assert acc.status == "active" and str(acc.review_id) == rid
    assert item.document_outcome_applied_at is not None
    # il verbale riporta la delibera
    from apps.management_review.models import ManagementReview
    from apps.management_review.report import build_report
    doc = build_report(ManagementReview.objects.get(pk=rid))
    assert any(s["heading"] == "Accettazioni del rischio deliberate" for s in doc["sections"])
    # deliberata: non è più in attesa
    assert risk_services.acceptances_awaiting_body(plant.pk) == []


def test_targeted_review_rejects_and_postpones(co, plant, threats):  # noqa: F811
    rejected = _self_managed_acceptance(co, plant, threats["malware"])
    postponed = _self_managed_acceptance(co, plant, threats["fire"])
    rid = _review(co, plant, "mirato")
    _api(co).post(f"{URL}{rid}/acceptance-items/",
                  {"acceptance_ids": [str(rejected.pk), str(postponed.pk)]}, format="json")
    _api(co).patch(f"{ITEMS}{_item(rid, rejected).pk}/",
                   {"document_outcome": "respinto", "discussion": "Serve una misura compensativa"}, format="json")
    _api(co).patch(f"{ITEMS}{_item(rid, postponed).pk}/", {"document_outcome": "rinviato"}, format="json")
    _close_and_approve(co, rid)

    rejected.refresh_from_db()
    postponed.refresh_from_db()
    assert rejected.status == "rejected" and rejected.close_reason == "Serve una misura compensativa"
    assert postponed.status == "pending" and postponed.review_id is None
    # il rinviato torna selezionabile nel riesame successivo
    nxt = _review(co, plant, "mirato")
    assert [r["id"] for r in _api(co).get(f"{URL}{nxt}/pending-acceptances/").data] == [str(postponed.pk)]


def test_one_open_review_at_a_time(co, plant, threats):  # noqa: F811
    acc = _self_managed_acceptance(co, plant, threats["malware"])
    first = _review(co, plant, "mirato")
    _add(co, first, acc)
    second = _review(co, plant, "mirato")
    assert _api(co).get(f"{URL}{second}/pending-acceptances/").data == []
    r = _api(co).post(f"{URL}{second}/acceptance-items/", {"acceptance_ids": [str(acc.pk)]}, format="json")
    assert r.data["added"] == [] and len(r.data["skipped"]) == 1


def test_org_scope_class_only_in_org_review(co, plant, threats):  # noqa: F811
    """Classi che la policy riserva all'organizzazione: le decide solo il
    riesame di organizzazione, non quello del sito."""
    risk_services.save_governance_policy(co, None, {"acceptance_matrix": {
        "medium": {"roles": [], "scope": "org", "requires_body": True},
    }})
    acc = _self_managed_acceptance(co, plant, threats["malware"])
    site = _review(co, plant, "mirato")
    org = _review(co, None, "mirato")
    assert _api(co).get(f"{URL}{site}/pending-acceptances/").data == []
    assert [r["id"] for r in _api(co).get(f"{URL}{org}/pending-acceptances/").data] == [str(acc.pk)]


def test_site_user_sees_only_own_site(co, plant, threats):  # noqa: F811
    other = _plant("RA-2")
    _self_managed_acceptance(co, plant, threats["malware"])
    mine = _self_managed_acceptance(co, other, threats["malware"])
    site_co = _user("mr_site", role="compliance_officer", scope="single_plant", plants=[other])
    site = _review(co, other, "mirato")
    assert [r["id"] for r in _api(site_co).get(f"{URL}{site}/pending-acceptances/").data] == [str(mine.pk)]
    # il riesame di organizzazione (che vede tutti i siti) non è nel suo perimetro
    org = _review(co, None, "mirato")
    assert _api(site_co).get(f"{URL}{org}/pending-acceptances/").status_code == 404


def test_revoked_after_session_is_not_applied(co, plant, threats):  # noqa: F811
    acc = _self_managed_acceptance(co, plant, threats["malware"])
    rid = _review(co, plant, "mirato")
    _add(co, rid, acc)
    item = _item(rid, acc)
    _api(co).patch(f"{ITEMS}{item.pk}/", {"document_outcome": "approvato"}, format="json")
    risk_services.revoke_acceptance(co, acc, "Rischio rivalutato")
    _close_and_approve(co, rid)
    item.refresh_from_db()
    acc.refresh_from_db()
    assert acc.status == "revoked" and item.document_outcome_applied_at is None
    assert item.document_outcome_error

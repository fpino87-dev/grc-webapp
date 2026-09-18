"""Riesame tenuto da un organo di governo: convocati proposti dai componenti,
presenze, approvazione in app da un consigliere con account o con delibera."""
from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

User = get_user_model()

URL = "/api/v1/management-review/reviews/"


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="GBR-1", name="Sito GBR", country="IT",
                                nis2_scope="essenziale", status="attivo")


@pytest.fixture
def co(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="gbr_co", email="co@gbr.test", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def director(db, plant):
    """Consigliere con account ma con un ruolo GRC che non legge i riesami."""
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="gbr_ad", email="ad@gbr.test", password="x",
                                 first_name="Paola", last_name="Neri")
    acc = UserPlantAccess.objects.create(user=u, role=GrcRole.CONTROL_OWNER, scope_type="single_plant")
    acc.scope_plants.add(plant)
    return u


@pytest.fixture
def board(db, director):
    from apps.governance.models import CommitteeMember, SecurityCommittee
    body = SecurityCommittee.objects.create(name="CdA", committee_type="cda")
    CommitteeMember.objects.create(committee=body, full_name="Paola Neri", position="Amministratore Delegato",
                                   body_role="presidente", user=director, valid_from=date(2025, 1, 1))
    CommitteeMember.objects.create(committee=body, full_name="Luca Verdi", position="CFO",
                                   valid_from=date(2025, 1, 1))
    CommitteeMember.objects.create(committee=body, full_name="Ex Consigliere",
                                   valid_from=date(2020, 1, 1), valid_until=date(2024, 12, 31))
    return body


def _api(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _ready(review_id):
    """Riunione chiusa e snapshot presente: pronta per l'approvazione."""
    from apps.management_review.models import ManagementReview
    ManagementReview.objects.filter(pk=review_id).update(
        status="completato", snapshot_generated_at=timezone.now(),
        snapshot_data={"generated_at": timezone.now().isoformat()},
    )


@pytest.mark.django_db
def test_create_with_body_proposes_active_members(co, board):
    resp = _api(co).post(URL, {"title": "Riesame 2026", "review_date": "2026-03-01",
                               "governing_body": str(board.id)}, format="json")
    assert resp.status_code == 201, resp.data
    detail = _api(co).get(f"{URL}{resp.data['id']}/").data
    names = [p["full_name"] for p in detail["participants"]]
    assert names == ["Paola Neri", "Luca Verdi"]  # presidente prima, ex escluso
    assert detail["chair_name"] == "Paola Neri"
    assert detail["participants"][0]["position"] == "Amministratore Delegato"


@pytest.mark.django_db
def test_body_must_govern_review_scope(co, plant):
    from apps.governance.models import SecurityCommittee
    from apps.plants.models import Plant
    other = Plant.objects.create(code="GBR-2", name="Altro", country="IT", nis2_scope="non_soggetto", status="attivo")
    site_body = SecurityCommittee.objects.create(name="Comitato altro sito")
    site_body.plants.add(other)
    client = _api(co)
    resp = client.post(URL, {"title": "R", "review_date": "2026-03-01", "plant": str(plant.id),
                             "governing_body": str(site_body.id)}, format="json")
    assert resp.status_code == 400
    # riesame di organizzazione: solo organi di organizzazione
    resp = client.post(URL, {"title": "R", "review_date": "2026-03-01",
                             "governing_body": str(site_body.id)}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_participants_validation(co, board):
    from apps.management_review.models import ManagementReview
    review = ManagementReview.objects.create(title="R", review_date=date(2026, 3, 1), governing_body=board)
    members = list(board.members.order_by("full_name"))
    client = _api(co)
    put = lambda rows: client.put(f"{URL}{review.id}/participants/", {"participants": rows}, format="json")  # noqa: E731

    assert put([{"member": str(members[0].id), "is_chair": True},
                {"member": str(members[1].id), "is_chair": True}]).status_code == 400  # due presidenti
    assert put([{"member": str(members[0].id), "is_chair": True, "attendance": "assente"}]).status_code == 400
    assert put([{"member": str(members[0].id), "attendance": "delegato"}]).status_code == 400  # manca delegato
    assert put([{"member": str(members[0].id)}, {"member": str(members[0].id)}]).status_code == 400  # doppione

    from apps.governance.models import SecurityCommittee
    stranger = SecurityCommittee.objects.create(name="Altro").members.create(
        full_name="Estraneo", valid_from=date(2025, 1, 1))
    assert put([{"member": str(stranger.id)}]).status_code == 400  # non è dell'organo

    resp = put([{"member": str(members[0].id), "attendance": "delegato", "delegate_name": "Avv. Rossi"}])
    assert resp.status_code == 200, resp.data


@pytest.mark.django_db
def test_director_sees_and_approves_only_own_body_reviews(co, board, director):
    from apps.management_review.models import ManagementReview
    mine = ManagementReview.objects.create(title="Del CdA", review_date=date(2026, 3, 1), governing_body=board)
    other = ManagementReview.objects.create(title="Altro", review_date=date(2026, 3, 1))
    _ready(mine.id)
    _ready(other.id)
    client = _api(director)

    titles = {r["title"] for r in client.get(URL).data["results"]}
    assert titles == {"Del CdA"}
    assert client.get(f"{URL}{mine.id}/").data["viewer_can_approve"] is True
    # decisioni e ordine del giorno restano ai ruoli: filtrati solo per sito
    assert client.get("/api/v1/management-review/review-actions/").status_code == 403
    assert client.get("/api/v1/management-review/agenda-items/").status_code == 403
    # nessun'altra scrittura
    assert client.patch(f"{URL}{mine.id}/", {"title": "X"}, format="json").status_code == 403
    assert client.post(f"{URL}{other.id}/approve/", {}, format="json").status_code == 404
    # la delibera la registra governance, non il consigliere
    assert client.post(f"{URL}{mine.id}/approve/", {"mode": "delibera", "resolution_ref": "1",
                                                     "resolution_date": "2026-03-02"}, format="json").status_code == 403

    resp = client.post(f"{URL}{mine.id}/approve/", {"note": "ok"}, format="json")
    assert resp.status_code == 200, resp.data
    assert resp.data["approval_mode"] == "in_app"
    assert resp.data["approved_member_name"] == "Paola Neri (Amministratore Delegato)"


@pytest.mark.django_db
def test_former_member_cannot_approve(co, board, director):
    from apps.management_review.models import ManagementReview
    board.members.filter(user=director).update(valid_until=date.today() - timedelta(days=1))
    review = ManagementReview.objects.create(title="R", review_date=date(2026, 3, 1), governing_body=board)
    _ready(review.id)
    assert _api(director).post(f"{URL}{review.id}/approve/", {}, format="json").status_code == 403


@pytest.mark.django_db
def test_approval_by_resolution(co, board):
    from apps.management_review.models import ManagementReview
    review = ManagementReview.objects.create(title="R", review_date=date(2026, 3, 1), governing_body=board)
    _ready(review.id)
    client = _api(co)
    base = {"mode": "delibera", "note": ""}
    assert client.post(f"{URL}{review.id}/approve/", base, format="json").status_code == 400  # estremi mancanti
    assert client.post(f"{URL}{review.id}/approve/", {**base, "resolution_ref": "12/2026",
                                                      "resolution_date": "2026-02-01"},
                       format="json").status_code == 400  # precede la riunione
    resp = client.post(f"{URL}{review.id}/approve/", {**base, "resolution_ref": "12/2026",
                                                      "resolution_date": "2026-03-10"}, format="json")
    assert resp.status_code == 200, resp.data
    assert resp.data["approval_mode"] == "delibera"
    assert resp.data["approval_resolution_ref"] == "12/2026"

    from apps.management_review.report.builder import build_report
    lines = dict(build_report(ManagementReview.objects.get(pk=review.id))["approval"]["lines"])
    assert lines["Approvato da"] == "CdA"
    assert "12/2026" in lines["Delibera"]


@pytest.mark.django_db
def test_minutes_freeze_participants(co, board):
    """Il verbale riporta nome e qualifica alla data del riesame, anche se poi
    la qualifica del componente cambia."""
    from apps.management_review.models import ManagementReview
    from apps.management_review.report.builder import build_report
    resp = _api(co).post(URL, {"title": "R", "review_date": "2026-03-01",
                               "governing_body": str(board.id)}, format="json")
    review_id = resp.data["id"]
    _ready(review_id)
    board.members.filter(full_name="Luca Verdi").update(position="Direttore Generale")
    doc = build_report(ManagementReview.objects.get(pk=review_id))
    table = next(s for s in doc["sections"] if s["heading"] == "Partecipanti")["blocks"][0]
    assert ["Luca Verdi", "CFO", "Membro", "Presente"] in table["rows"]


@pytest.mark.django_db
def test_list_query_count_does_not_grow_with_reviews(co, board):
    """Partecipanti, presidente e `viewer_can_approve` senza query per riga."""
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    client = _api(co)

    def count():
        with CaptureQueriesContext(connection) as q:
            assert client.get(URL).status_code == 200
        return len(q)

    client.post(URL, {"title": "R1", "review_date": "2026-03-01", "governing_body": str(board.id)}, format="json")
    one = count()
    for i in range(3):
        client.post(URL, {"title": f"R{i + 2}", "review_date": "2026-03-01",
                          "governing_body": str(board.id)}, format="json")
    assert count() == one

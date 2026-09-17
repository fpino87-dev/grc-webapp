"""Sintesi executive con bozza IA (human-in-the-loop) e relazione HTML/PDF."""
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.management_review.models import ManagementReview, ReviewAction
from apps.management_review.services import generate_snapshot

User = get_user_model()
pytestmark = pytest.mark.django_db
URL = "/api/v1/management-review/reviews/"


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="sumu", email="sum@test.com", password="x",
                                 first_name="Giulia", last_name="Bianchi")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def review(client, user):
    from apps.plants.models import Plant
    plant = Plant.objects.create(code="SUM-P", name="Stabilimento Sud", country="IT",
                                 nis2_scope="non_soggetto", status="attivo")
    rid = client.post(URL, {"plant": str(plant.id), "title": "Riesame 2026", "review_date": "2026-03-10",
                            "chair": user.id}, format="json").data["id"]
    r = ManagementReview.objects.get(pk=rid)
    item = r.agenda_items.get(code="contesto")
    item.discussion = "Giulia Bianchi segnala il nuovo cliente OEM per lo Stabilimento Sud"
    item.save()
    ReviewAction.objects.create(review=r, agenda_item=item, description="Aggiornare l'analisi del contesto")
    generate_snapshot(r, user)
    return r


def _fake_route(captured):
    def _route(**kwargs):
        captured.update(kwargs)
        return {"text": "Sintesi: [PERSONA_1] ha illustrato il contesto.", "provider": "anthropic",
                "model": "claude-x", "used_fallback": False, "tokens_used": 10, "interaction_id": None}
    return _route


def test_ai_draft_is_pseudonymised_and_not_in_minutes(client, review):
    captured = {}
    with mock.patch("apps.ai_engine.router.route", side_effect=_fake_route(captured)):
        resp = client.post(f"{URL}{review.id}/summary-draft/", {"lang": "en"}, format="json")
    assert resp.status_code == 200, resp.data
    assert "Giulia Bianchi" not in captured["prompt"] and "[PERSONA_1]" in captured["prompt"]
    assert captured["sanitize"] is True and captured["task_type"] == "review_summary"
    assert captured["plant_ids"] == [review.plant_id]
    assert "English" in captured["prompt"]
    # la bozza ripristina il nome ma NON entra nel verbale finché non è accettata
    assert resp.data["executive_summary_draft"] == "Sintesi: Giulia Bianchi ha illustrato il contesto."
    assert resp.data["executive_summary"] == ""


def test_accept_edited_draft_records_ai_metadata(client, review, user):
    with mock.patch("apps.ai_engine.router.route", side_effect=_fake_route({})):
        client.post(f"{URL}{review.id}/summary-draft/", {}, format="json")
    with mock.patch("apps.ai_engine.router.confirm_output") as confirm:
        resp = client.post(f"{URL}{review.id}/summary/", {"text": "Testo rivisto dal CISO."}, format="json")
    assert resp.status_code == 200
    meta = resp.data["executive_summary_meta"]
    assert resp.data["executive_summary"] == "Testo rivisto dal CISO."
    assert resp.data["executive_summary_draft"] == ""
    assert meta["ai_assisted"] is True and meta["edited"] is True and meta["accepted_by"] == user.id
    assert meta["model"] == "claude-x"
    confirm.assert_not_called()  # interaction_id assente nel fake


def test_manual_summary_without_ai(client, review):
    resp = client.post(f"{URL}{review.id}/summary/", {"text": "Scritta a mano."}, format="json")
    assert resp.status_code == 200
    assert resp.data["executive_summary_meta"]["ai_assisted"] is False


def test_discard_draft(client, review):
    with mock.patch("apps.ai_engine.router.route", side_effect=_fake_route({})):
        client.post(f"{URL}{review.id}/summary-draft/", {}, format="json")
    resp = client.delete(f"{URL}{review.id}/summary-draft/")
    assert resp.status_code == 200 and resp.data["executive_summary_draft"] == ""


def test_ai_unavailable_returns_503(client, review):
    from apps.ai_engine.router import LlmUnavailable
    with mock.patch("apps.ai_engine.router.route", side_effect=LlmUnavailable("down")):
        resp = client.post(f"{URL}{review.id}/summary-draft/", {}, format="json")
    assert resp.status_code == 503


def test_ai_draft_requires_snapshot(client, user):
    rid = client.post(URL, {"title": "Senza dati", "review_date": "2026-03-10"}, format="json").data["id"]
    assert client.post(f"{URL}{rid}/summary-draft/", {}, format="json").status_code == 400


def test_report_html_and_pdf(client, review, user):
    ManagementReview.objects.filter(pk=review.pk).update(
        executive_summary="Il SGSI è adeguato.",
        executive_summary_meta={"ai_assisted": True, "provider": "anthropic", "model": "claude-x", "edited": False,
                                "accepted_by_name": "Giulia Bianchi", "accepted_at": timezone.now().isoformat()},
    )
    html = client.get(f"{URL}{review.id}/report/").content.decode()
    assert "b) Cambiamenti nei fattori esterni e interni" in html
    assert "Aggiornare l&#x27;analisi del contesto" in html
    assert "supporto dell&#x27;intelligenza artificiale (anthropic/claude-x)" in html
    assert "Presieduto da" in html and "Giulia Bianchi" in html

    resp = client.get(f"{URL}{review.id}/report/", {"fmt": "pdf"})
    assert resp.status_code == 200 and resp["Content-Type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"
    assert client.get(f"{URL}{review.id}/report/", {"fmt": "docx"}).status_code == 400

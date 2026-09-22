"""Bozza IA della discussione dei punti all'ordine del giorno (M13 + M20)."""
from datetime import date
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APIClient

User = get_user_model()
pytestmark = pytest.mark.django_db

URL = "/api/v1/management-review/agenda-items/"

AI_RESULT = {
    "text": "I dati mostrano una copertura dei controlli in crescita e due non conformità aperte.",
    "provider": "cloud", "model": "claude-opus-5", "interaction_id": "abc-123", "used_fallback": False,
}


@pytest.fixture
def co(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="ai_co", email="co@ai.test", password="x",
                                 first_name="Marta", last_name="Conti")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="AI-1", name="Sito AI", country="IT",
                                nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def item(db, plant, co):
    from apps.management_review.models import ManagementReview
    from apps.management_review.services import ensure_iso_agenda

    review = ManagementReview.objects.create(title="Riesame", review_date=date(2026, 3, 1),
                                             plant=plant, created_by=co)
    ensure_iso_agenda(review)
    ManagementReview.objects.filter(pk=review.pk).update(
        snapshot_generated_at=timezone.now(),
        snapshot_data={"generated_at": timezone.now().isoformat(),
                       "documenti": {"approvati": 3, "non_approvati_obbligatori": 1,
                                     "elenco_non_approvati": [{"title": "Policy accessi", "status": "bozza"}]},
                       "audit": {"nc_aperte_maggiori": 1}},
    )
    from apps.management_review.models import ReviewAgendaItem

    return ReviewAgendaItem.objects.select_related("review").get(
        review_id=review.pk, code="prestazioni",
    )


def _api(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def test_prompt_contains_only_item_data(item):
    from apps.management_review.services.agenda_ai import build_agenda_prompt

    prompt = build_agenda_prompt(item, "it")
    assert "Policy accessi" in prompt           # dati del punto
    assert "non conformità" in prompt.lower() or "conformi" in prompt.lower()
    assert "ISTRUZIONI" in prompt


def test_draft_does_not_touch_the_minutes(item, co):
    with patch("apps.ai_engine.router.route", return_value=AI_RESULT):
        resp = _api(co).post(f"{URL}{item.id}/discussion-draft/", {"lang": "it"}, format="json")

    assert resp.status_code == 200, resp.data
    item.refresh_from_db()
    # la bozza resta separata: il verbale non cambia finché non la si accetta
    assert item.discussion == ""
    assert item.discussion_draft == AI_RESULT["text"]
    assert item.discussion_draft_meta["model"] == "claude-opus-5"


def test_accept_moves_draft_into_minutes_with_provenance(item, co):
    with patch("apps.ai_engine.router.route", return_value=AI_RESULT):
        _api(co).post(f"{URL}{item.id}/discussion-draft/", {"lang": "it"}, format="json")

    testo = AI_RESULT["text"] + " La direzione chiede un piano entro giugno."
    with patch("apps.ai_engine.router.confirm_output") as confirm:
        resp = _api(co).post(f"{URL}{item.id}/discussion/", {"text": testo}, format="json")

    assert resp.status_code == 200, resp.data
    item.refresh_from_db()
    assert item.discussion == testo
    assert item.discussion_draft == ""
    meta = item.discussion_meta
    assert meta["ai_assisted"] is True and meta["edited"] is True
    assert meta["accepted_by_name"] == "Marta Conti"
    confirm.assert_called_once()


def test_discard_leaves_no_trace(item, co):
    with patch("apps.ai_engine.router.route", return_value=AI_RESULT):
        _api(co).post(f"{URL}{item.id}/discussion-draft/", {"lang": "it"}, format="json")

    resp = _api(co).delete(f"{URL}{item.id}/discussion-draft/")
    assert resp.status_code == 200
    item.refresh_from_db()
    assert item.discussion_draft == "" and item.discussion == ""


def test_draft_requires_snapshot(plant, co):
    from apps.management_review.models import ManagementReview
    from apps.management_review.services import draft_agenda_discussion, ensure_iso_agenda

    review = ManagementReview.objects.create(title="Senza dati", review_date=date(2026, 3, 1),
                                             plant=plant, created_by=co)
    ensure_iso_agenda(review)
    with pytest.raises(ValidationError):
        draft_agenda_discussion(review.agenda_items.first(), co, "it")


def test_approved_review_is_not_draftable(item, co):
    from apps.management_review.models import ManagementReview
    from apps.management_review.services import draft_agenda_discussion

    ManagementReview.objects.filter(pk=item.review_id).update(approval_status="approvato")
    item.refresh_from_db()
    with pytest.raises(ValidationError):
        draft_agenda_discussion(item, co, "it")


def test_draft_is_not_writable_via_patch(item, co):
    resp = _api(co).patch(f"{URL}{item.id}/", {"discussion_draft": "testo iniettato"}, format="json")
    assert resp.status_code == 200
    item.refresh_from_db()
    assert item.discussion_draft == ""


def test_report_declares_ai_assisted_discussion(item, co):
    """Il verbale dichiara i punti scritti con l'aiuto dell'IA."""
    from apps.management_review.report.builder import build_report

    with patch("apps.ai_engine.router.route", return_value=AI_RESULT):
        _api(co).post(f"{URL}{item.id}/discussion-draft/", {"lang": "it"}, format="json")
    with patch("apps.ai_engine.router.confirm_output"):
        _api(co).post(f"{URL}{item.id}/discussion/", {"text": AI_RESULT["text"]}, format="json")

    item.refresh_from_db()
    report = build_report(item.review)
    testi = [
        str(b.get("text")) for section in report["sections"]
        for b in section.get("blocks", []) if b.get("type") == "paragraph"
    ]
    assert any("intelligenza artificiale" in t and "Marta Conti" in t for t in testi)

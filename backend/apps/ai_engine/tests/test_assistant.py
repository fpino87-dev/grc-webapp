"""Test del GRC Compliance Assistant (M20 — assistant/start, assistant/explain)."""
from __future__ import annotations

import datetime
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def plant_a(db):
    from apps.plants.models import Plant

    return Plant.objects.create(
        code="PA",
        name="Plant A",
        country="IT",
        nis2_scope="essenziale",
        status="attivo",
    )


@pytest.fixture
def plant_b(db):
    from apps.plants.models import Plant

    return Plant.objects.create(
        code="PB",
        name="Plant B",
        country="IT",
        nis2_scope="non_soggetto",
        status="attivo",
    )


@pytest.fixture
def co_user_org(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess

    user = User.objects.create_user(
        username="co_org",
        email="co_org@test.com",
        password="test",
    )
    UserPlantAccess.objects.create(
        user=user,
        role=GrcRole.COMPLIANCE_OFFICER,
        scope_type="org",
    )
    return user


@pytest.fixture
def pm_user_plant_a(db, plant_a):
    from apps.auth_grc.models import GrcRole, UserPlantAccess

    user = User.objects.create_user(
        username="pm_a",
        email="pm_a@test.com",
        password="test",
    )
    access = UserPlantAccess.objects.create(
        user=user,
        role=GrcRole.PLANT_MANAGER,
        scope_type="single_plant",
    )
    access.scope_plants.add(plant_a)
    return user


def _client(user) -> APIClient:
    c = APIClient()
    c.force_authenticate(user=user)
    return c


# ─── /assistant/start/ ─────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_start_requires_plant_id(co_user_org):
    res = _client(co_user_org).post("/api/v1/ai/assistant/start/", {}, format="json")
    assert res.status_code == 400
    assert "plant_id" in res.json()["error"]


@pytest.mark.django_db
def test_start_blocks_other_plant(pm_user_plant_a, plant_b):
    """Plant manager con accesso solo a Plant A non puo' analizzare Plant B."""
    res = _client(pm_user_plant_a).post(
        "/api/v1/ai/assistant/start/",
        {"plant_id": str(plant_b.id)},
        format="json",
    )
    assert res.status_code == 403


@pytest.mark.django_db
def test_start_returns_expected_structure(co_user_org, plant_a):
    res = _client(co_user_org).post(
        "/api/v1/ai/assistant/start/",
        {"plant_id": str(plant_a.id)},
        format="json",
    )
    assert res.status_code == 200
    data = res.json()
    assert set(["plant", "summary", "gaps", "gaps_total", "gaps_truncated"]).issubset(data.keys())
    assert data["plant"]["id"] == str(plant_a.id)
    assert isinstance(data["gaps"], list)


@pytest.mark.django_db
def test_expired_documents_are_detected(co_user_org, plant_a):
    """Documento con expiry_date scaduto deve apparire come gap document_expired."""
    from apps.documents.models import Document

    yesterday = timezone.now().date() - datetime.timedelta(days=5)
    doc = Document.objects.create(
        title="Politica scaduta",
        category="politica",
        document_type="policy",
        status="approvato",
        plant=plant_a,
        expiry_date=yesterday,
    )

    res = _client(co_user_org).post(
        "/api/v1/ai/assistant/start/",
        {"plant_id": str(plant_a.id)},
        format="json",
    )
    assert res.status_code == 200
    gaps = res.json()["gaps"]
    found = [g for g in gaps if g["kind"] == "document_expired" and g["ref_id"] == str(doc.id)]
    assert found, f"Atteso gap document_expired per il doc; ottenuti: {[g['kind'] for g in gaps]}"
    assert found[0]["category"] == "documents"
    assert found[0]["urgency"] in ("red", "yellow", "green")


# ─── /assistant/explain/ ───────────────────────────────────────────────────────


@pytest.mark.django_db
def test_explain_requires_payload(co_user_org, plant_a):
    """Senza 'gap' nel body → 400 prima di chiamare l'LLM."""
    res = _client(co_user_org).post(
        "/api/v1/ai/assistant/explain/",
        {"plant_id": str(plant_a.id)},
        format="json",
    )
    assert res.status_code == 400


@pytest.mark.django_db
def test_explain_blocks_other_plant(pm_user_plant_a, plant_b):
    res = _client(pm_user_plant_a).post(
        "/api/v1/ai/assistant/explain/",
        {"plant_id": str(plant_b.id), "gap": {"kind": "document_expired", "title": "x", "subtitle": "y", "details": {}}},
        format="json",
    )
    assert res.status_code == 403


@pytest.mark.django_db
@patch("apps.ai_engine.router.route")
def test_explain_creates_interaction_log(mock_route, co_user_org, plant_a):
    from apps.ai_engine.models import AiInteractionLog

    mock_route.return_value = {
        "text": "spiegazione mock",
        "interaction_id": "00000000-0000-0000-0000-000000000001",
        "provider": "anthropic",
        "model": "claude-haiku-4-5",
        "used_fallback": False,
        "tokens_used": 0,
    }

    gap = {
        "kind": "document_expired",
        "category": "documents",
        "ref_id": "00000000-0000-0000-0000-000000000099",
        "title": "Politica scaduta",
        "subtitle": "Scaduto da 5 giorni",
        "details": {"document_type": "policy", "status": "approvato"},
        "priority_score": 95,
        "urgency": "red",
        "frontend_url": "/documents?id=x",
    }
    res = _client(co_user_org).post(
        "/api/v1/ai/assistant/explain/",
        {"plant_id": str(plant_a.id), "gap": gap},
        format="json",
    )
    assert res.status_code == 200, res.json()
    body = res.json()
    assert body["explanation"] == "spiegazione mock"
    assert body["provider"] == "anthropic"
    mock_route.assert_called_once()
    call_kwargs = mock_route.call_args.kwargs
    assert call_kwargs["task_type"] == "assistant_explain"
    assert call_kwargs["sanitize"] is True
    assert call_kwargs["plant_ids"] == [plant_a.pk]


# ─── tool unitari ──────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_get_expired_documents_respects_plant_access(co_user_org, pm_user_plant_a, plant_a, plant_b):
    """Doc su plant_b non deve essere visto da pm_user_plant_a."""
    from apps.ai_engine.agent_tools import get_expired_documents
    from apps.documents.models import Document

    yesterday = timezone.now().date() - datetime.timedelta(days=2)
    Document.objects.create(
        title="Doc B scaduto",
        category="politica",
        document_type="policy",
        status="approvato",
        plant=plant_b,
        expiry_date=yesterday,
    )

    out_pm = get_expired_documents(pm_user_plant_a, plant_b.id)
    assert out_pm == []  # accesso negato → lista vuota
    out_co = get_expired_documents(co_user_org, plant_b.id)
    assert len(out_co) == 1
    assert out_co[0]["kind"] == "expired"

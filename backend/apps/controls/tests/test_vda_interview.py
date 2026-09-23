"""
Intervista guidata VDA ISA: requisiti dal framework, domande IA in cache,
risposte salvate, bozza IA non salvata (human-in-the-loop), conferma
dell'interazione IA al salvataggio della descrizione.
"""
import json
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.controls.services.vda_interview import parse_requirements

User = get_user_model()

URL = "/api/v1/controls/instances/"

DESC_BASE = (
    "Requisiti (must):\n"
    "+ A policy is prepared and is released by the organization.\n"
    "+ The requirements for information security have been determined:\n"
    "  - The requirements are adapted to the organization's goals,\n"
    "Requisiti (should):\n"
    "+ Periodic review of the policies is established.\n"
    "Requisiti aggiuntivi per alta protezione:\n"
    "+ Policies are reviewed by management.\n"
)
DESC_VH = (
    "Requisiti aggiuntivi per protezione molto alta (VDA ISA §1.1.1):\n"
    "+ Additional requirements for monitoring are determined (C, I, A)\n"
)


def _route_result(payload, interaction_id=None):
    return {
        "text": json.dumps(payload), "provider": "anthropic", "model": "m",
        "used_fallback": False, "interaction_id": interaction_id,
    }


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="int_user", email="int@test.com", password="test")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def setup(db):
    from apps.controls.models import Control, ControlInstance, ControlMapping, Framework
    from apps.plants.models import Plant, PlantFramework
    plant = Plant.objects.create(
        code="INT-P", name="Interview Plant", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )
    fw_l2 = Framework.objects.create(code="TISAX_L2", name="L2", version="6", published_at=timezone.localdate())
    fw_l3 = Framework.objects.create(code="TISAX_L3", name="L3", version="6", published_at=timezone.localdate())
    for fw in (fw_l2, fw_l3):
        PlantFramework.objects.create(plant=plant, framework=fw, active_from=timezone.localdate(),
                                      level="AL3", active=True)
    base = Control.objects.create(framework=fw_l2, external_id="ISA-1.1.1", level="L2",
                                  translations={"en": {"title": "Policies", "description": DESC_BASE}})
    vh = Control.objects.create(framework=fw_l3, external_id="ISA-1.1.1-VH", level="L3",
                                translations={"en": {"title": "Policies VH", "description": DESC_VH}})
    ControlMapping.objects.create(source_control=vh, target_control=base, relationship="extends")
    base_inst = ControlInstance.objects.create(plant=plant, control=base)
    vh_inst = ControlInstance.objects.create(plant=plant, control=vh)
    return {"plant": plant, "base": base_inst, "vh": vh_inst}


def test_parse_requirements_levels_and_continuations():
    reqs = parse_requirements(DESC_BASE)
    assert [r["level"] for r in reqs] == ["must", "must", "should", "high"]
    assert reqs[1]["text"] == (
        "The requirements for information security have been determined: "
        "- The requirements are adapted to the organization's goals,"
    )
    assert parse_requirements(DESC_VH)[0]["level"] == "very_high"
    # id stabile = hash del testo
    assert parse_requirements(DESC_BASE)[0]["id"] == reqs[0]["id"]


@pytest.mark.django_db
def test_get_interview_vh_includes_base_and_caches_questions(client, setup):
    vh = setup["vh"]

    def fake_route(**kwargs):
        ids = [line.split('"')[1] for line in kwargs["prompt"].splitlines() if line.startswith('- id "')]
        assert kwargs["sanitize"] is False  # testo normativo pubblico
        return _route_result({"questions": {i: f"Domanda {i}?" for i in ids}})

    with patch("apps.ai_engine.tasks_ai.route", side_effect=fake_route) as mocked:
        resp = client.get(f"{URL}{vh.id}/vda-interview/?lang=it")
        assert resp.status_code == 200
        assert mocked.call_count == 2  # una chiamata per controllo (base + VH)
        reqs = resp.data["requirements"]
        assert [r["level"] for r in reqs] == ["must", "must", "should", "high", "very_high"]
        assert reqs[0]["source"] == "L2" and reqs[-1]["source"] == "L3"
        assert all(r["question"].startswith("Domanda") for r in reqs)

        # seconda apertura: domande dalla cache, nessuna chiamata IA
        client.get(f"{URL}{vh.id}/vda-interview/?lang=it")
        assert mocked.call_count == 2


@pytest.mark.django_db
def test_get_interview_without_ai_returns_requirements(client, setup):
    from apps.ai_engine.router import AiNotConfigured
    with patch("apps.ai_engine.tasks_ai.route", side_effect=AiNotConfigured("x")):
        resp = client.get(f"{URL}{setup['base'].id}/vda-interview/?lang=pl")
    assert resp.status_code == 200
    assert resp.data["ai_error"] == "not_configured"
    assert len(resp.data["requirements"]) == 4
    assert all(r["question"] == "" and r["text_en"] for r in resp.data["requirements"])


@pytest.mark.django_db
def test_save_answers_filters_unknown_ids_and_audits_counts(client, setup):
    from core.audit import AuditLog
    inst = setup["base"]
    rid = parse_requirements(DESC_BASE)[0]["id"]
    resp = client.post(f"{URL}{inst.id}/vda-interview/", {
        "lang": "it", "answers": {rid: "  Politica approvata dal CdA  ", "bogus": "x", parse_requirements(DESC_BASE)[1]["id"]: ""},
    }, format="json")
    assert resp.status_code == 200 and resp.data["answered"] == 1
    inst.refresh_from_db()
    assert inst.implementation_interview["answers"] == {rid: "Politica approvata dal CdA"}
    assert inst.implementation_interview["lang"] == "it"
    log = AuditLog.objects.get(entity_id=inst.pk, action_code="control.vda_interview_saved")
    assert log.payload == {"answered": 1, "lang": "it"}


@pytest.mark.django_db
def test_draft_returns_text_but_does_not_save_description(client, setup):
    inst = setup["base"]
    reqs = parse_requirements(DESC_BASE)
    answers = {reqs[0]["id"]: "Sì, approvata dal CdA", reqs[3]["id"]: "No, non ancora"}
    captured = {}

    def fake_route(**kwargs):
        captured.update(kwargs)
        return _route_result({
            "draft_en": "The policy is released by the board.",
            "draft_local": "La politica è approvata dal CdA.",
            "not_implemented": [reqs[3]["id"], "invented-id"],
        })

    with patch("apps.ai_engine.tasks_ai.route", side_effect=fake_route):
        resp = client.post(f"{URL}{inst.id}/vda-interview/draft/", {"lang": "it", "answers": answers},
                           format="json")
    assert resp.status_code == 200
    assert resp.data["draft_en"] == "The policy is released by the board."
    assert resp.data["draft_local"] == "La politica è approvata dal CdA."
    assert resp.data["not_implemented"] == [reqs[3]["id"]]  # id inventati scartati
    assert resp.data["unanswered"] == [reqs[1]["id"], reqs[2]["id"]]
    assert captured["sanitize"] is True and captured["task_type"] == "vda_interview"
    assert "Sì, approvata dal CdA" in captured["prompt"]
    inst.refresh_from_db()
    assert inst.implementation_description == ""  # human-in-the-loop
    assert inst.implementation_interview["answers"] == answers


@pytest.mark.django_db
def test_draft_without_ai_configured_returns_400(client, setup):
    from apps.ai_engine.router import AiNotConfigured
    with patch("apps.ai_engine.tasks_ai.route", side_effect=AiNotConfigured("x")):
        resp = client.post(f"{URL}{setup['base'].id}/vda-interview/draft/", {"lang": "it", "answers": {}},
                           format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_set_implementation_confirms_own_ai_interaction(client, user, setup):
    from apps.ai_engine.models import AiInteractionLog
    from core.audit import AuditLog
    inst = setup["base"]
    own = AiInteractionLog.objects.create(
        user_id=user.pk, function="vda_interview", module_source="M03", entity_id=inst.pk,
        model_used="a/m", input_hash="h", output_ai="draft",
    )
    resp = client.post(f"{URL}{inst.id}/set-implementation/", {
        "implementation_description": "Final text", "ai_interaction_id": str(own.pk),
    }, format="json")
    assert resp.status_code == 200
    own.refresh_from_db()
    assert own.output_human_final == "Final text" and own.confirmed_at is not None
    log = AuditLog.objects.get(entity_id=inst.pk, action_code="control.implementation_description_set")
    assert log.payload["ai_assisted"] is True


@pytest.mark.django_db
def test_set_implementation_ignores_foreign_ai_interaction(client, setup):
    import uuid
    from apps.ai_engine.models import AiInteractionLog
    inst = setup["base"]
    other = AiInteractionLog.objects.create(
        user_id=uuid.uuid4(), function="vda_interview", module_source="M03", entity_id=inst.pk,
        model_used="a/m", input_hash="h", output_ai="draft",
    )
    client.post(f"{URL}{inst.id}/set-implementation/", {
        "implementation_description": "Text", "ai_interaction_id": str(other.pk),
    }, format="json")
    other.refresh_from_db()
    assert other.confirmed_at is None


@pytest.mark.django_db
def test_interview_only_for_tisax(client, setup):
    from apps.controls.models import Control, ControlInstance, Framework
    iso = Framework.objects.create(code="ISO27001", name="ISO", version="1", published_at=timezone.localdate())
    ctrl = Control.objects.create(framework=iso, external_id="A.5.1", translations={})
    inst = ControlInstance.objects.create(plant=setup["plant"], control=ctrl)
    assert client.get(f"{URL}{inst.id}/vda-interview/").status_code in (400, 404)


@pytest.mark.django_db
def test_interview_forbidden_for_auditor(setup):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    auditor = User.objects.create_user(username="aud", email="aud@test.com", password="x")
    UserPlantAccess.objects.create(user=auditor, role=GrcRole.EXTERNAL_AUDITOR, scope_type="org")
    c = APIClient()
    c.force_authenticate(user=auditor)
    assert c.get(f"{URL}{setup['base'].id}/vda-interview/").status_code == 403

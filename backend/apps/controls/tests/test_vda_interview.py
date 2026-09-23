"""
Intervista guidata VDA ISA "da auditor": requisiti dal framework, temi IA in
cache, fotografia dei temi e lingua bloccata, verifica su 2 giri con
approfondimenti, bozza IA non salvata (human-in-the-loop), conferma
dell'interazione IA al salvataggio della descrizione.
"""
import json
import re
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


def _ids_in(prompt):
    return re.findall(r"^- \[([0-9a-f]{10})\]", prompt, re.M)


class FakeAI:
    """Simula il provider IA riconoscendo il passo dal prompt."""

    def __init__(self, coverage="missing", followups=1, maturity=2):
        self.calls = []
        self.coverage = coverage
        self.followups = followups
        self.maturity = maturity

    def __call__(self, **kwargs):
        prompt = kwargs["prompt"]
        self.calls.append(kwargs)
        ids = _ids_in(prompt)
        if "Group the requirements" in prompt:
            half = len(ids) // 2
            return _route_result({"topics": [
                {"question": "Quali documenti?", "auditor_intent": "Capire i documenti",
                 "what_to_mention": ["policy", "manuale"], "example": "Il documento [codice]...",
                 "req_ids": ids[:half]},
                {"question": "Come li comunicate?", "auditor_intent": "Capire la diffusione",
                 "what_to_mention": ["intranet"], "example": "Pubblicati su [strumento]",
                 "req_ids": ids[half:-1] + ["invented"]},  # l'ultimo id "dimenticato"
            ]})
        if "review round" in prompt:
            return _route_result({
                "coverage": {i: self.coverage for i in ids[:-1]} | {"invented": "covered"},
                "followups": [{"question": f"Approfondimento {n}?", "req_ids": ids[:1]}
                              for n in range(self.followups + 3)],
                "evidence": [{"item": "Verbale CdA", "linked": "POL-1 Policy"},
                             {"item": "Registro", "linked": "Inventato"}],
                "maturity": {"supported_level": self.maturity, "comment": "Manca la revisione"},
                "summary": "Base presente.",
            }, interaction_id=None)
        return _route_result({"draft_en": "The policy exists.", "draft_local": "La policy esiste."})


@pytest.mark.django_db
def test_get_interview_generates_topics_once_and_covers_all_requirements(client, setup):
    vh = setup["vh"]
    ai = FakeAI()
    with patch("apps.ai_engine.tasks_ai.route", side_effect=ai):
        resp = client.get(f"{URL}{vh.id}/vda-interview/?lang=it")
        assert resp.status_code == 200
        assert len(ai.calls) == 1 and ai.calls[0]["sanitize"] is False
        data = resp.data
        # VH: requisiti del base (4) + propri (1)
        assert [r["level"] for r in data["requirements"]] == ["must", "must", "should", "high", "very_high"]
        topics = data["topics"]
        assert [t["id"] for t in topics] == ["t1", "t2"]
        assigned = [rid for t in topics for rid in t["req_ids"]]
        assert "invented" not in assigned
        assert sorted(assigned) == sorted(r["id"] for r in data["requirements"])  # dimenticato → ultimo tema
        assert data["rounds_used"] == 0 and data["max_rounds"] == 2

        client.get(f"{URL}{vh.id}/vda-interview/?lang=it")
        assert len(ai.calls) == 1  # cache


@pytest.mark.django_db
def test_get_interview_without_ai_returns_only_requirements(client, setup):
    from apps.ai_engine.router import AiNotConfigured
    with patch("apps.ai_engine.tasks_ai.route", side_effect=AiNotConfigured("x")):
        resp = client.get(f"{URL}{setup['base'].id}/vda-interview/?lang=pl")
    assert resp.status_code == 200
    assert resp.data["ai_error"] == "not_configured"
    assert resp.data["topics"] == [] and len(resp.data["requirements"]) == 4


@pytest.mark.django_db
def test_save_snapshots_topics_and_locks_language(client, setup):
    from core.audit import AuditLog
    inst = setup["base"]
    with patch("apps.ai_engine.tasks_ai.route", side_effect=FakeAI()):
        resp = client.post(f"{URL}{inst.id}/vda-interview/", {
            "lang": "it", "answers": {"t1": "  POL-ISMS-01 approvata dal CdA  ", "bogus": "x"},
        }, format="json")
    assert resp.status_code == 200
    inst.refresh_from_db()
    state = inst.implementation_interview
    assert state["answers"] == {"t1": "POL-ISMS-01 approvata dal CdA"}
    assert state["lang"] == "it" and len(state["topics"]) == 2
    log = AuditLog.objects.get(entity_id=inst.pk, action_code="control.vda_interview_saved")
    assert log.payload["answered"] == 1 and "POL" not in str(log.payload)

    # riaperta in un'altra lingua: stessi temi, lingua originale, nessuna chiamata IA
    with patch("apps.ai_engine.tasks_ai.route", side_effect=AssertionError("no AI")):
        again = client.get(f"{URL}{inst.id}/vda-interview/?lang=pl")
    assert again.data["lang"] == "it" and again.data["answers"]["t1"].startswith("POL")


@pytest.mark.django_db
def test_review_rounds_followups_and_limit(client, setup):
    from core.audit import AuditLog
    inst = setup["base"]
    ai = FakeAI(followups=1)
    with patch("apps.ai_engine.tasks_ai.route", side_effect=ai):
        # senza risposte la verifica non parte
        empty = client.post(f"{URL}{inst.id}/vda-interview/review/", {"lang": "it", "answers": {}}, format="json")
        assert empty.status_code == 400

        r1 = client.post(f"{URL}{inst.id}/vda-interview/review/",
                         {"lang": "it", "answers": {"t1": "Policy approvata"}}, format="json")
        assert r1.status_code == 200
        review = r1.data["reviews"][0]
        assert review["round"] == 1
        assert len(review["followups"]) == 3  # massimo 3
        assert [f["id"] for f in r1.data["followups"]] == ["f1_1", "f1_2", "f1_3"]
        assert "invented" not in review["coverage"]
        # requisito non valutato dall'IA → missing
        assert set(review["coverage"].values()) == {"missing"}
        assert review["evidence"][1]["linked"] == ""  # nome non collegato → scartato
        assert ai.calls[-1]["sanitize"] is True
        assert "review round 1 of 2" in ai.calls[-1]["prompt"]

        r2 = client.post(f"{URL}{inst.id}/vda-interview/review/", {
            "lang": "it", "answers": {"t1": "Policy approvata"},
            "followup_answers": {"f1_1": "Revisione annuale", "zzz": "x"},
        }, format="json")
        assert r2.data["rounds_used"] == 2
        assert r2.data["followup_answers"] == {"f1_1": "Revisione annuale"}
        assert "Follow-up Q: Approfondimento 0?\nA: Revisione annuale" in ai.calls[-1]["prompt"]
        assert "LAST round" in ai.calls[-1]["prompt"]

        r3 = client.post(f"{URL}{inst.id}/vda-interview/review/",
                         {"lang": "it", "answers": {"t1": "Policy approvata"}}, format="json")
        assert r3.status_code == 400

        # ricominciare la verifica azzera giri e approfondimenti, non le risposte
        reset = client.post(f"{URL}{inst.id}/vda-interview/", {
            "lang": "it", "answers": {"t1": "Policy approvata"}, "reset_reviews": True,
        }, format="json")
        assert reset.data["rounds_used"] == 0 and reset.data["followups"] == []
        assert reset.data["answers"] == {"t1": "Policy approvata"}
    log = AuditLog.objects.filter(entity_id=inst.pk, action_code="control.vda_interview_reviewed").first()
    assert set(log.payload) == {"round", "covered", "partial", "missing", "supported_maturity"}


@pytest.mark.django_db
def test_draft_uses_review_gaps_and_is_not_saved(client, setup):
    inst = setup["base"]
    reqs = parse_requirements(DESC_BASE)
    ai = FakeAI(coverage="missing")
    with patch("apps.ai_engine.tasks_ai.route", side_effect=ai):
        client.post(f"{URL}{inst.id}/vda-interview/review/",
                    {"lang": "it", "answers": {"t1": "Sì, approvata dal CdA"}}, format="json")
        resp = client.post(f"{URL}{inst.id}/vda-interview/draft/",
                           {"lang": "it", "answers": {"t1": "Sì, approvata dal CdA"}}, format="json")
    assert resp.status_code == 200
    assert resp.data["draft_en"] == "The policy exists."
    # gaps = obbligatori (must/high/very_high) "missing" nell'ultima verifica; il should no
    assert set(resp.data["gaps"]) == {reqs[0]["id"], reqs[1]["id"], reqs[3]["id"]}
    prompt = ai.calls[-1]["prompt"]
    assert ai.calls[-1]["sanitize"] is True
    assert "Sì, approvata dal CdA" in prompt and "State each fact ONCE" in prompt
    inst.refresh_from_db()
    assert inst.implementation_description == ""  # human-in-the-loop


@pytest.mark.django_db
def test_draft_without_answers_or_ai(client, setup):
    from apps.ai_engine.router import AiNotConfigured
    with patch("apps.ai_engine.tasks_ai.route", side_effect=FakeAI()):
        no_answers = client.post(f"{URL}{setup['base'].id}/vda-interview/draft/",
                                 {"lang": "it", "answers": {}}, format="json")
    assert no_answers.status_code == 400
    with patch("apps.ai_engine.tasks_ai.route", side_effect=AiNotConfigured("x")):
        no_ai = client.post(f"{URL}{setup['vh'].id}/vda-interview/draft/",
                            {"lang": "it", "answers": {"t1": "x"}}, format="json")
    assert no_ai.status_code == 400


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

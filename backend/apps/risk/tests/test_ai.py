"""Supporto IA al risk assessment: proposte ripulite e mai applicate, controlli
di coerenza deterministici, feedback solo di chi ha chiesto la proposta."""
import json
from unittest.mock import patch

import pytest

from apps.risk import services
from apps.risk.models import InformationClass, RiskAssessment, ThreatCatalogEntry

from .test_register import _client, _completed_risk, _eval, _user


def _fake_route(text):
    def route(**kwargs):
        return {"text": text, "provider": "test", "model": "m", "used_fallback": False,
                "model_substituted": None, "tokens_used": 0, "interaction_id": None}
    return route


@pytest.mark.django_db
def test_ai_draft_is_cleaned_and_not_applied(org_user, plant, threats, cycle):
    risk = services.create_risk(org_user, plant, {"asset_type": "IT", "threat": threats["malware"]})
    answer = json.dumps({
        "vulnerability": "Patch MES in ritardo", "probability": 9, "probability_method": "fer",
        "probability_rationale": "Controlli con lacune", "impacts": {"operational": 4, "legal": "x", "foo": 5},
        "treatment": "ignorare", "current_class": "very_low",
    })
    with patch("apps.ai_engine.tasks_ai.route", _fake_route(answer)):
        res = _client(org_user).post(f"/api/v1/risk/assessments/{risk.pk}/ai-draft/")
    assert res.status_code == 200, res.content
    proposal = res.json()["proposal"]
    assert proposal == {"vulnerability": "Patch MES in ritardo", "probability_method": "fer",
                        "probability_rationale": "Controlli con lacune", "impact_operational": 4}
    risk.refresh_from_db()
    assert risk.vulnerability == "" and risk.probability is None  # niente applicato


@pytest.mark.django_db
def test_ai_draft_requires_register_write(site_user, org_user, other_plant, threats):
    services.start_cycle(org_user, other_plant, "primo")
    risk = services.create_risk(org_user, other_plant, {"asset_type": "IT", "threat": threats["malware"]})
    with patch("apps.ai_engine.tasks_ai.route", _fake_route("{}")):
        res = _client(site_user).post(f"/api/v1/risk/assessments/{risk.pk}/ai-draft/")
    assert res.status_code in (403, 404)


@pytest.mark.django_db
def test_ai_not_configured_is_explained(org_user, plant, threats, cycle):
    risk = services.create_risk(org_user, plant, {"asset_type": "IT", "threat": threats["malware"]})
    res = _client(org_user).post(f"/api/v1/risk/assessments/{risk.pk}/ai-draft/")
    assert res.status_code == 400 and res.json()["error"]


@pytest.mark.django_db
def test_ai_measures_map_controls_and_cap_deadline(org_user, plant, threats, cycle):
    import datetime

    from apps.controls.models import Control, ControlInstance, Framework

    fw = Framework.objects.create(code="VDA_X", name="VDA", version="6", published_at=datetime.date(2024, 1, 1))
    ctrl = Control.objects.create(framework=fw, external_id="ISA-5.2.6", translations={"it": {"title": "Malware"}})
    ci = ControlInstance.objects.create(plant=plant, control=ctrl, status="gap")
    risk = _completed_risk(org_user, plant, threats["malware"])  # Critical: misure entro 3 mesi
    answer = json.dumps({"measures": [
        {"action": "EDR sulle postazioni MES", "expected_effect": "probabilita", "weeks": 52, "control": 1},
        {"action": "", "weeks": 2},
        {"action": "Segmentazione OT", "expected_effect": "boh", "control": 99},
    ]})
    with patch("apps.ai_engine.tasks_ai.route", _fake_route(answer)):
        res = _client(org_user).post(f"/api/v1/risk/assessments/{risk.pk}/ai-measures/")
    measures = res.json()["measures"]
    assert len(measures) == 2
    assert measures[0]["control_instance"] == str(ci.pk)
    limit = datetime.date.today() + datetime.timedelta(days=90)
    assert datetime.date.fromisoformat(measures[0]["due_date"]) <= limit
    assert measures[1]["control_instance"] is None and measures[1]["expected_effect"] == ""
    assert not risk.mitigation_plans.exists()  # niente applicato


@pytest.mark.django_db
def test_consistency_checks(org_user, plant, threats, cycle):
    secret = InformationClass.objects.create(name="CAD", confidentiality="very_high")
    no_info = _completed_risk(org_user, plant, threats["malware"])  # C senza informazioni, Critical senza piano
    codes = {(f["code"], f["risk_id"]) for f in services.register_consistency_checks(plant)}
    assert ("confidentiality_without_information", str(no_info.pk)) in codes
    assert ("high_without_plan", str(no_info.pk)) in codes
    services.update_risk(org_user, no_info, {"information_classes": [secret]})
    codes = {f["code"] for f in services.register_consistency_checks(plant)}
    assert "confidentiality_without_information" not in codes
    # stessa minaccia, impatti molto diversi
    services.create_risk(org_user, plant, {**_eval(org_user), "threat": threats["malware"],
                                           "impact_operational": 1, "impact_rationale": "Postazione di ufficio isolata"})
    assert "impact_spread" in {f["code"] for f in services.register_consistency_checks(plant)}


@pytest.mark.django_db
def test_review_endpoint_with_ai_findings(org_user, plant, threats, cycle):
    risk = _completed_risk(org_user, plant, threats["malware"])
    answer = json.dumps({"findings": [{"n": 1, "issue": "Impatto 4 motivato con un disagio lieve"}, {"n": 7, "issue": "x"}]})
    with patch("apps.ai_engine.tasks_ai.route", _fake_route(answer)):
        res = _client(org_user).post(f"/api/v1/risk/assessments/review/?plant={plant.pk}", {"ai": True}, format="json")
    body = res.json()
    assert res.status_code == 200 and body["checks"]
    assert body["ai"]["findings"] == [{"risk_id": str(risk.pk), "risk_name": services.risk_label(risk),
                                       "issue": "Impatto 4 motivato con un disagio lieve", "suggestion": ""}]
    # senza IA: solo le regole, nessuna chiamata
    res = _client(org_user).post(f"/api/v1/risk/assessments/review/?plant={plant.pk}", {}, format="json")
    assert res.json()["ai"] is None


@pytest.mark.django_db
def test_ai_summary(org_user, plant, threats, cycle):
    _completed_risk(org_user, plant, threats["malware"])
    with patch("apps.ai_engine.tasks_ai.route", _fake_route(json.dumps({"summary": "Situazione sotto controllo."}))):
        res = _client(org_user).post(f"/api/v1/risk/assessments/ai-summary/?plant={plant.pk}")
    assert res.status_code == 200 and res.json()["summary"] == "Situazione sotto controllo."
    digest = services.register_ai_digest(plant)
    assert digest["per_classe"]["critical"] == 1 and digest["principali_non_accettati"]


@pytest.mark.django_db
def test_ai_feedback_only_by_requester(org_user, plant, threats, cycle):
    from apps.ai_engine.models import AiInteractionLog

    risk = services.create_risk(org_user, plant, {"asset_type": "IT", "threat": threats["malware"]})
    log = AiInteractionLog.objects.create(user_id=org_user.pk, function="risk_draft", module_source="M06",
                                          entity_id=risk.pk, model_used="t/m", input_hash="x", output_ai="{}")
    other = _user("other-org")
    url = "/api/v1/risk/assessments/ai-feedback/"
    assert _client(other).post(url, {"interaction_id": str(log.pk), "action": "confirm"}, format="json").status_code == 404
    res = _client(org_user).post(url, {"interaction_id": str(log.pk), "action": "confirm",
                                       "final_text": "probabilità, impatto"}, format="json")
    assert res.status_code == 200
    log.refresh_from_db()
    assert log.confirmed_at and log.output_human_final == "probabilità, impatto"
    assert RiskAssessment.objects.filter(pk=risk.pk).exists()
    assert ThreatCatalogEntry.objects.exists()


@pytest.mark.django_db
def test_ai_identify_proposes_only_missing_threats(org_user, plant, threats, cycle):
    from apps.risk.tests.test_register import _objective

    extra = ThreatCatalogEntry.objects.create(code="IN_PHI", asset_types=["IT"], cia=["C"], source="catalog",
                                              translations={"it": {"title": "Phishing"}})
    services.create_risk(org_user, plant, {"asset_type": "IT", "threat": threats["malware"]})  # già coperta
    objective = _objective()
    answer = json.dumps({"items": [
        {"threat": "IN_PHI", "applicable": True, "vulnerability": "Posta senza filtro", "probability": 4,
         "probability_rationale": "Campagne frequenti", "impacts": {"customer": 4, "foo": 3},
         "objectives": ["1", 1, 99], "process": 42, "current_class": "low"},
        {"threat": "IN_MAL", "applicable": True, "vulnerability": "già valutata"},  # non richiesta
        {"threat": "XX_FAKE", "applicable": False, "reason": "inventata"},
    ]})
    with patch("apps.ai_engine.tasks_ai.route", _fake_route(answer)):
        res = _client(org_user).post(f"/api/v1/risk/assessments/ai-identify/?plant={plant.pk}",
                                     {"asset_type": "IT"}, format="json")
    assert res.status_code == 200, res.content
    body = res.json()
    assert body["remaining"] == 0
    assert body["items"] == [{
        "threat_id": str(extra.pk), "threat_code": "IN_PHI", "applicable": True, "reason": "",
        "proposal": {"vulnerability": "Posta senza filtro", "probability": 4,
                     "probability_rationale": "Campagne frequenti", "impact_customer": 4},
        "critical_process": None, "business_objectives": [str(objective.pk)], "information_classes": [],
    }]
    assert RiskAssessment.objects.filter(plant=plant).count() == 1  # niente creato


@pytest.mark.django_db
def test_ai_identify_not_applicable_requires_reason(threats):
    items = [{"threat": "IN_MAL", "applicable": False, "reason": ""},
             {"threat": "LO_FUO", "applicable": False, "reason": "Nessuna sede fisica propria"}]
    out = services.validate_ai_identification(items, list(threats.values()), {"processes": [], "objectives": []})
    assert [(r["threat_code"], r["applicable"]) for r in out] == [("LO_FUO", False)]


@pytest.mark.django_db
def test_ai_identify_apply_creates_drafts_and_not_applicable(org_user, plant, threats, cycle):
    from apps.risk.tests.test_register import _objective

    objective = _objective()
    url = f"/api/v1/risk/assessments/ai-identify-apply/?plant={plant.pk}"
    items = [{"threat_id": str(threats["malware"].pk), "applicable": True,
              "proposal": {"vulnerability": "Patch in ritardo", "probability": 9, "impact_operational": 4,
                           "current_class": "very_low", "owner": str(org_user.pk)},
              "business_objectives": [str(objective.pk)]},
             {"threat_id": str(threats["fire"].pk), "applicable": False, "reason": "tipologia diversa"}]
    res = _client(org_user).post(url, {"asset_type": "IT", "items": items}, format="json")
    assert res.status_code == 201, res.content
    assert res.json() == {"created": res.json()["created"], "not_applicable": 0, "skipped": 1}
    risk = RiskAssessment.objects.get(pk=res.json()["created"][0])
    assert risk.status == "bozza" and risk.vulnerability == "Patch in ritardo"
    assert risk.probability is None and risk.impact_operational == 4 and risk.owner_id is None
    assert list(risk.business_objectives.all()) == [objective]
    # seconda volta: la coppia è coperta, niente duplicati
    res = _client(org_user).post(url, {"asset_type": "IT", "items": items[:1]}, format="json")
    assert res.json()["created"] == [] and res.json()["skipped"] == 1
    # non applicabile: motivo obbligatorio, come a mano
    na = {"threat_id": str(threats["fire"].pk), "applicable": False, "reason": "Sito senza sede propria"}
    res = _client(org_user).post(url, {"asset_type": "SEDE", "items": [na]}, format="json")
    assert res.json()["not_applicable"] == 1
    assert RiskAssessment.objects.get(plant=plant, threat=threats["fire"]).applicable is False


@pytest.mark.django_db
def test_ai_identify_requires_register_write(site_user, org_user, other_plant, threats):
    services.start_cycle(org_user, other_plant, "primo")
    with patch("apps.ai_engine.tasks_ai.route", _fake_route("{}")):
        res = _client(site_user).post(f"/api/v1/risk/assessments/ai-identify/?plant={other_plant.pk}",
                                      {"asset_type": "IT"}, format="json")
    assert res.status_code in (403, 404)
    res = _client(site_user).post(f"/api/v1/risk/assessments/ai-identify-apply/?plant={other_plant.pk}",
                                  {"asset_type": "IT", "items": [{"threat_id": str(threats["malware"].pk)}]},
                                  format="json")
    assert res.status_code in (403, 404)
    assert not RiskAssessment.objects.filter(plant=other_plant).exists()


@pytest.mark.django_db
def test_ai_draft_proposes_objectives_information_and_process(org_user, plant, threats, cycle):
    from apps.bia.models import CriticalProcess
    from apps.risk.tests.test_register import _objective

    objective = _objective()
    cad = InformationClass.objects.create(name="CAD cliente", confidentiality="very_high")
    other = InformationClass.objects.create(plant=None, name="Listini", confidentiality="normal")
    process = CriticalProcess.objects.create(plant=plant, name="Produzione linea", criticality=5)
    risk = services.create_risk(org_user, plant, {"asset_type": "IT", "threat": threats["malware"]})
    links = services.ai_link_candidates(plant)
    assert links["information"][:2] == [cad, other]  # le più riservate prima
    n_obj = links["objectives"].index(objective) + 1
    answer = json.dumps({
        "probability_method": " FER ", "probability": 3, "impacts": {"operational": 4, "customer": "4"},
        "objectives": [n_obj, 999], "information": ["1"], "process": 1,
    })
    with patch("apps.ai_engine.tasks_ai.route", _fake_route(answer)):
        res = _client(org_user).post(f"/api/v1/risk/assessments/{risk.pk}/ai-draft/")
    body = res.json()
    assert body["proposal"] == {
        "probability_method": "fer", "probability": 3, "impact_operational": 4, "impact_customer": 4,
        "business_objectives": [str(objective.pk)], "information_classes": [str(cad.pk)],
        "critical_process": str(process.pk),
    }
    assert body["names"]["information"][str(cad.pk)] == "CAD cliente"
    risk.refresh_from_db()
    assert not risk.business_objectives.exists()  # niente applicato


@pytest.mark.django_db
def test_ai_identify_apply_links_information(org_user, plant, threats, cycle):
    cad = InformationClass.objects.create(name="CAD cliente", confidentiality="very_high")
    items = [{"threat_id": str(threats["malware"].pk), "applicable": True,
              "proposal": {"probability": 3, "impact_operational": 2}, "information_classes": [str(cad.pk)]}]
    res = _client(org_user).post(f"/api/v1/risk/assessments/ai-identify-apply/?plant={plant.pk}",
                                 {"asset_type": "IT", "items": items}, format="json")
    risk = RiskAssessment.objects.get(pk=res.json()["created"][0])
    assert list(risk.information_classes.all()) == [cad]
    assert risk.impact == 5  # soglia di riservatezza: informazioni Segrete su minaccia C


@pytest.mark.django_db
def test_ai_measures_on_draft_risk(org_user, plant, threats, cycle):
    risk = services.create_risk(org_user, plant, {
        "asset_type": "IT", "threat": threats["malware"], "probability": 4, "impact_operational": 4,
        "treatment": "mitigare",
    })
    assert risk.status == "bozza" and risk.current_class
    answer = json.dumps({"measures": [{"action": "MFA per gli accessi remoti", "expected_effect": "probabilita"}]})
    with patch("apps.ai_engine.tasks_ai.route", _fake_route(answer)):
        res = _client(org_user).post(f"/api/v1/risk/assessments/{risk.pk}/ai-measures/")
    assert res.status_code == 200 and res.json()["measures"][0]["action"] == "MFA per gli accessi remoti"


@pytest.mark.django_db
def test_ai_prompts_ask_why_not_measures_in_treatment_rationale(org_user, plant, threats, cycle):
    """La motivazione del trattamento è il perché della scelta: le misure vanno nel piano."""
    prompts = []

    def route(**kwargs):
        prompts.append(kwargs["prompt"])
        return _fake_route("{}")(**kwargs)

    risk = services.create_risk(org_user, plant, {"asset_type": "IT", "threat": threats["malware"]})
    with patch("apps.ai_engine.tasks_ai.route", route):
        _client(org_user).post(f"/api/v1/risk/assessments/{risk.pk}/ai-draft/")
    assert prompts and all("NON elenca le misure" in p and "piano di" in p for p in prompts)

"""Guardia: il riesame di direzione (M13) e il Reporting (M18) danno gli
stessi numeri sullo stesso perimetro — conformità per framework, quadro per
sito, rischi oltre la soglia di accettabilità, processi critici senza BCP."""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def user(db):
    return User.objects.create_user(username="mrnum", email="mrnum@test.com", password="x")


def _plant(code):
    from apps.plants.models import Plant
    return Plant.objects.create(code=code, name=f"Sito {code}", country="IT", nis2_scope="non_soggetto", status="attivo")


def _framework(code, plant):
    from apps.controls.models import Framework
    from apps.plants.models import PlantFramework
    fw = Framework.objects.filter(code=code).first() or Framework.objects.create(
        code=code, name=code, version="1", published_at=timezone.localdate(),
    )
    PlantFramework.objects.create(plant=plant, framework=fw, active_from=timezone.localdate())
    return fw


def _instance(plant, fw, ext_id, status, user):
    from apps.controls.models import Control, ControlInstance
    control = Control.objects.filter(framework=fw, external_id=ext_id).first() or Control.objects.create(
        framework=fw, external_id=ext_id, translations={"it": {"title": ext_id}}, evidence_requirement={},
    )
    return ControlInstance.objects.create(plant=plant, control=control, status=status, created_by=user)


def _risk(plant, user, prob, impact):
    from apps.risk.models import RiskAssessment
    return RiskAssessment.objects.create(
        plant=plant, name=f"R{prob}x{impact}", assessment_type="IT", threat_category="malware_ransomware",
        probability=prob, impact=impact, status="completato", created_by=user,
    )


@pytest.fixture
def perimeter(user):
    """Due siti: A con TISAX L2+L3 (un L2 sostituito dal VH, un N/A), soglia di
    rischio di sito 9, un processo critico coperto solo da una bozza; B con
    ISO 27001 e la soglia di organizzazione 14."""
    from apps.bcp.models import BcpPlan
    from apps.bia.models import CriticalProcess
    from apps.controls.models import ControlMapping
    from apps.risk.models import RiskAppetitePolicy

    a, b = _plant("NUM-A"), _plant("NUM-B")
    l2, l3 = _framework("TISAX_L2", a), _framework("TISAX_L3", a)
    _instance(a, l2, "L2-1", "compliant", user)
    _instance(a, l2, "L2-2", "gap", user)
    base = _instance(a, l2, "L2-3", "gap", user)
    _instance(a, l2, "L2-4", "na", user)
    vh = _instance(a, l3, "L3-VH", "compliant", user)
    ControlMapping.objects.create(source_control=vh.control, target_control=base.control, relationship="extends")
    iso = _framework("ISO27001", b)
    _instance(b, iso, "A.5.1", "compliant", user)
    _instance(b, iso, "A.5.2", "parziale", user)

    yesterday = timezone.localdate() - timedelta(days=1)
    RiskAppetitePolicy.objects.create(plant=None, max_acceptable_score=14, max_red_risks_count=3, valid_from=yesterday)
    RiskAppetitePolicy.objects.create(plant=a, max_acceptable_score=9, max_red_risks_count=1, valid_from=yesterday)
    _risk(a, user, 2, 5)   # 10 > 9 (sito A)
    _risk(a, user, 2, 4)   # 8
    _risk(b, user, 3, 4)   # 12 < 14 (organizzazione)
    _risk(b, user, 3, 5)   # 15 > 14

    draft_only = CriticalProcess.objects.create(plant=a, name="Solo bozza", criticality=5)
    BcpPlan.objects.create(plant=a, title="Bozza", status="bozza", critical_process=draft_only, created_by=user)
    covered = CriticalProcess.objects.create(plant=b, name="Coperto", criticality=4)
    plan = BcpPlan.objects.create(plant=b, title="Approvato", status="approvato", created_by=user)
    plan.critical_processes.add(covered)
    return a, b


def _snapshot(plant, user):
    from apps.management_review.models import ManagementReview
    from apps.management_review.services import generate_snapshot
    review = ManagementReview.objects.create(
        plant=plant, title="Riesame", review_date=timezone.localdate(), created_by=user,
    )
    return generate_snapshot(review, user)


@pytest.mark.parametrize("site", ["NUM-A", "NUM-B", None])
def test_review_snapshot_matches_reporting(perimeter, user, site):
    from apps.plants.models import Plant
    from apps.reporting.services import compliance_overview, risk_bia_bcp

    plant = Plant.objects.get(code=site) if site else None
    plant_id = str(plant.pk) if plant else None
    snap = _snapshot(plant, user)
    overview = {f["code"]: f for f in compliance_overview(plant_id)["frameworks"]}
    risk = risk_bia_bcp(plant_id)

    assert snap["compliance_rule"] == 2
    assert set(snap["frameworks"]) == set(overview)
    for code, fw in snap["frameworks"].items():
        assert fw["pct_compliant"] == overview[code]["pct_compliant"], code
        assert fw["total"] == overview[code]["total"], code
        assert fw["by_status"]["gap"] == overview[code]["gap"], code
        assert fw["superseded_by_extender"] == overview[code]["superseded_by_extender"], code

    assert snap["rischi"]["oltre_soglia"] == risk["kpis"]["risks_over_appetite"]
    assert snap["rischi"]["soglia"]["max_acceptable_score"] == risk["appetite"]["max_acceptable_score"]
    assert snap["bcp"]["processi_critici_senza_bcp"] == risk["kpis"]["bia_critical_no_bcp"]


def test_expected_values_on_the_perimeter(perimeter, user):
    """I numeri attesi, per esteso: se cambia la regola, cambia qui."""
    a, _b = perimeter
    snap = _snapshot(a, user)
    l2 = snap["frameworks"]["TISAX_L2"]
    assert (l2["total"], l2["by_status"]["compliant"], l2["pct_compliant"]) == (2, 1, 50.0)
    assert (l2["na_excluded"], l2["superseded_by_extender"]) == (1, 1)
    assert [g["control__external_id"] for g in l2["gap_controls"]] == ["L2-2"]   # L2-3 si valuta sul VH
    assert snap["rischi"]["oltre_soglia"] == 1          # soglia di sito 9
    assert snap["bcp"]["processi_critici_senza_bcp"] == 1   # la bozza non copre


def test_org_sites_block_matches_reporting(perimeter, user):
    from apps.controls.services import get_compliance_summary
    from apps.reporting.services import risk_bia_bcp
    snap = _snapshot(None, user)
    for row in snap["siti"]:
        assert row["pct_compliant"] == get_compliance_summary(row["plant_id"])["pct_compliant"]
        assert row["rischi_oltre_soglia"] == risk_bia_bcp(row["plant_id"])["kpis"]["risks_over_appetite"]


def test_kpi_snapshot_matches_reporting(perimeter, user):
    from apps.controls.services import get_compliance_summary
    from apps.management_review.services import get_kpi_snapshot
    from apps.reporting.services import dashboard_summary, risk_bia_bcp
    a, _b = perimeter
    k = get_kpi_snapshot(a.pk)
    assert k["pct_compliant"] == get_compliance_summary(str(a.pk))["pct_compliant"] == dashboard_summary(str(a.pk))["pct_compliant"]
    assert k["risks_high"] == risk_bia_bcp(str(a.pk))["kpis"]["risks_over_appetite"]


def test_legacy_snapshot_still_renders(perimeter, user):
    """Un verbale congelato con le regole precedenti (senza oltre_soglia,
    rischi_oltre_soglia, compliance_rule) si costruisce ancora con le vecchie
    etichette."""
    from apps.management_review.report.builder import _compliance_blocks, _risk_blocks
    legacy = {
        "frameworks": {"ISO27001": {"framework_name": "ISO", "total": 3, "pct_compliant": 33.3,
                                    "by_status": {"compliant": 1, "gap": 2}, "gap_controls": []}},
        "rischi": {"rosso": 2, "giallo": 1, "verde": 0, "senza_piano": 1, "top_critici": [], "elenco_accettati": []},
    }
    comp = _compliance_blocks(legacy)
    assert len(comp) == 1   # niente nota sulla regola
    risk = _risk_blocks(legacy)
    assert str(risk[0]["items"][0][0]) == "Rischi critici"

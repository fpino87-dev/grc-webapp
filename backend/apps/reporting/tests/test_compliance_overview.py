"""Tab Compliance del Reporting: regola unica di conformità (stesso numero in
Reporting, dashboard_summary, snapshot settimanale e Assistente), sintesi per
framework, confronto siti, dettaglio per dominio ed export."""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="cmp_u", email="cmpu@test.com", password="x")


def _plant(code):
    from apps.plants.models import Plant
    return Plant.objects.create(code=code, name=f"Plant {code}", country="IT", nis2_scope="non_soggetto", status="attivo")


def _framework(code, plant=None, active=True):
    from apps.controls.models import Framework
    from apps.plants.models import PlantFramework
    fw = Framework.objects.filter(code=code).first() or Framework.objects.create(
        code=code, name=code.replace("_", " "), version="1", published_at=timezone.localdate(),
    )
    if plant is not None:
        PlantFramework.objects.create(plant=plant, framework=fw, active_from=timezone.localdate(), active=active)
    return fw


def _domain(fw, code, order=0):
    from apps.controls.models import ControlDomain
    return ControlDomain.objects.create(framework=fw, code=code, order=order, translations={"it": {"name": f"Dominio {code}"}})


def _instance(plant, fw, ext_id, status, user, domain=None):
    from apps.controls.models import Control, ControlInstance
    control = Control.objects.filter(framework=fw, external_id=ext_id).first() or Control.objects.create(
        framework=fw, external_id=ext_id, domain=domain,
        translations={"it": {"title": f"Controllo {ext_id}"}}, evidence_requirement={},
    )
    return ControlInstance.objects.create(plant=plant, control=control, status=status, created_by=user)


@pytest.fixture
def tisax_site(db, user):
    """Sito con TISAX L2 e L3 attivi: L2 ha 4 controlli, uno dei quali (L2-3)
    sostituito dal VH di L3; più un N/A."""
    from apps.controls.models import ControlMapping
    plant = _plant("CMP-A")
    l2 = _framework("TISAX_L2", plant)
    l3 = _framework("TISAX_L3", plant)
    d1, d2 = _domain(l2, "IS", 1), _domain(l2, "PP", 2)
    _instance(plant, l2, "L2-1", "compliant", user, d1)
    _instance(plant, l2, "L2-2", "gap", user, d2)
    base = _instance(plant, l2, "L2-3", "gap", user, d2)
    _instance(plant, l2, "L2-4", "na", user, d1)
    vh = _instance(plant, l3, "L3-VH", "compliant", user)
    ControlMapping.objects.create(
        source_control=vh.control, target_control=base.control, relationship="extends",
    )
    return plant


@pytest.mark.django_db
def test_superseded_base_excluded_like_controls_list(tisax_site):
    from apps.controls.services import get_compliance_summary
    s = get_compliance_summary(str(tisax_site.pk), "TISAX_L2")
    assert s["total"] == 2          # L2-1 conforme + L2-2 gap; L2-3 sostituito, L2-4 N/A
    assert s["compliant"] == 1
    assert s["gap"] == 1
    assert s["na_excluded"] == 1
    assert s["superseded_by_extender"] == 1
    assert s["covered_by_extender"] == 1   # chiave legacy dell'Assistente
    assert s["pct_compliant"] == 50.0


@pytest.mark.django_db
def test_base_not_superseded_when_extender_framework_inactive(user):
    from apps.controls.models import ControlMapping
    from apps.controls.services import get_compliance_summary
    plant = _plant("CMP-B")
    l2 = _framework("TISAX_L2", plant)
    l3 = _framework("TISAX_L3", plant, active=False)
    base = _instance(plant, l2, "L2-3", "gap", user)
    vh = _instance(plant, l3, "L3-VH", "compliant", user)
    ControlMapping.objects.create(source_control=vh.control, target_control=base.control, relationship="extends")
    s = get_compliance_summary(str(plant.pk), "TISAX_L2")
    assert s["total"] == 1 and s["gap"] == 1 and s["superseded_by_extender"] == 0


@pytest.mark.django_db
def test_same_percentage_everywhere(tisax_site):
    """Reporting, dashboard_summary e snapshot danno lo stesso numero."""
    from apps.reporting.models import IsmsKpiSnapshot
    from apps.reporting.services import compliance_overview, dashboard_summary
    from apps.reporting.tasks import COMPLIANCE_METHOD_VERSION, generate_weekly_kpi_snapshots

    overview = {f["code"]: f for f in compliance_overview(str(tisax_site.pk))["frameworks"]}
    generate_weekly_kpi_snapshots()
    snap = IsmsKpiSnapshot.objects.get(plant=tisax_site, framework_code="TISAX_L2")
    assert snap.pct_compliant == overview["TISAX_L2"]["pct_compliant"] == 50.0
    assert snap.controls_total == overview["TISAX_L2"]["total"]
    assert snap.method_version == COMPLIANCE_METHOD_VERSION

    # dashboard_summary: insieme dei framework attivi (L2 effettivi + VH)
    dash = dashboard_summary(str(tisax_site.pk))
    assert dash["controls_total"] == 3
    assert dash["controls_compliant"] == 2
    assert dash["pct_compliant"] == round(2 / 3 * 100, 1)


@pytest.mark.django_db
def test_overview_trend_marks_legacy_and_ends_today(tisax_site):
    from apps.reporting.models import IsmsKpiSnapshot
    from apps.reporting.services import compliance_overview
    today = timezone.localdate()
    IsmsKpiSnapshot.objects.create(
        plant=tisax_site, framework_code="TISAX_L2", week_start=today - timedelta(days=21),
        pct_compliant=10.0, method_version=1,
    )
    IsmsKpiSnapshot.objects.create(
        plant=tisax_site, framework_code="TISAX_L2", week_start=today - timedelta(days=14),
        pct_compliant=40.0, method_version=2,
    )
    fw = next(f for f in compliance_overview(str(tisax_site.pk))["frameworks"] if f["code"] == "TISAX_L2")
    assert [p["legacy"] for p in fw["trend"]] == [True, False, False]
    assert fw["trend"][-1]["live"] is True
    assert fw["trend"][-1]["pct_compliant"] == 50.0
    # variazione solo fra valori con la regola attuale: 50 - 40, non 50 - 10
    assert fw["delta"] == 10.0


@pytest.mark.django_db
def test_overview_org_has_plant_matrix_only_without_plant(tisax_site, user):
    from apps.reporting.services import compliance_overview
    other = _plant("CMP-C")
    iso = _framework("ISO27001", other)
    _instance(other, iso, "A.5.1", "compliant", user)

    org = compliance_overview(None)
    assert {f["code"] for f in org["frameworks"]} == {"ISO27001", "TISAX_L2", "TISAX_L3"}
    rows = {p["code"]: p["cells"] for p in org["plants"]}
    assert set(rows["CMP-A"]) == {"TISAX_L2", "TISAX_L3"}
    assert rows["CMP-C"]["ISO27001"]["pct_compliant"] == 100.0
    assert compliance_overview(str(tisax_site.pk))["plants"] is None


@pytest.mark.django_db
def test_domains_sorted_most_exposed_first(tisax_site):
    from apps.reporting.services import compliance_domains
    out = compliance_domains(str(tisax_site.pk), "TISAX_L2", "it")
    assert [d["code"] for d in out["domains"]] == ["PP", "IS"]
    pp, is_ = out["domains"]
    assert (pp["gap"], pp["superseded_by_extender"], pp["pct_compliant"]) == (1, 1, 0)
    assert (is_["compliant"], is_["na_excluded"], is_["pct_compliant"]) == (1, 1, 100.0)
    assert pp["name"] == "Dominio PP"


@pytest.fixture
def sa_client(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="cmp_sa@test.com", email="cmp_sa@test.com", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.SUPER_ADMIN, scope_type="org")
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.mark.django_db
def test_endpoints_and_csv(sa_client, tisax_site):
    res = sa_client.get("/api/v1/reporting/compliance-overview/", {"plant": str(tisax_site.pk)})
    assert res.status_code == 200 and res.data["frameworks"]
    res = sa_client.get("/api/v1/reporting/compliance-domains/", {"plant": str(tisax_site.pk), "framework": "TISAX_L2"})
    assert res.status_code == 200 and len(res.data["domains"]) == 2
    res = sa_client.get(
        "/api/v1/reporting/compliance-domains/",
        {"plant": str(tisax_site.pk), "framework": "TISAX_L2", "export": "csv", "lang": "it"},
    )
    assert res.status_code == 200
    lines = res.content.decode().strip().splitlines()
    assert len(lines) == 2                      # intestazione + L2-2 (L2-3 sostituito, esclusa)
    assert "L2-2" in lines[1] and "Gap" in lines[1]


@pytest.mark.django_db
def test_org_view_requires_org_scope(tisax_site):
    """Senza sito la vista è aggregata su tutti i siti: solo scope org."""
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="cmp_pm@test.com", email="cmp_pm@test.com", password="x")
    acc = UserPlantAccess.objects.create(user=u, role=GrcRole.PLANT_MANAGER, scope_type="single_plant")
    acc.scope_plants.add(tisax_site)
    other = _plant("CMP-D")
    c = APIClient()
    c.force_authenticate(user=u)
    assert c.get("/api/v1/reporting/compliance-overview/", {"plant": str(tisax_site.pk)}).status_code == 200
    assert c.get("/api/v1/reporting/compliance-overview/").status_code == 403
    assert c.get("/api/v1/reporting/compliance-overview/", {"plant": str(other.pk)}).status_code == 403
    assert c.get("/api/v1/reporting/compliance-domains/", {"plant": str(other.pk), "framework": "TISAX_L2"}).status_code == 403

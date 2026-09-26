"""Test dei numeri del Reporting (M18) — P1-1.

Coprono le funzioni pure di `reporting/services.py` estratte dalle view: i numeri
che vedono direzione e auditor devono essere verificabili indipendentemente da
Request/Response.
"""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


# ───────────────────────────────────────────────────────────────────────────
# Fixtures
# ───────────────────────────────────────────────────────────────────────────
@pytest.fixture
def user(db):
    return User.objects.create_user(username="rep_svc", email="repsvc@test.com", password="x")


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="REP-A", name="Plant Rep A", country="IT",
        nis2_scope="essenziale", status="attivo",
    )


@pytest.fixture
def other_plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="REP-B", name="Plant Rep B", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


def make_risk(plant, user, prob, impact, status="completato", **extra):
    """Crea un RiskAssessment; score = prob*impact (ricalcolato in save())."""
    from apps.risk.models import RiskAssessment
    return RiskAssessment.objects.create(
        plant=plant,
        name=extra.pop("name", f"R{prob}x{impact}"),
        assessment_type="IT",
        threat_category=extra.pop("threat_category", "malware_ransomware"),
        probability=prob,
        impact=impact,
        status=status,
        created_by=user,
        **extra,
    )


# ───────────────────────────────────────────────────────────────────────────
# risk_summary
# ───────────────────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_risk_summary_empty():
    from apps.reporting.services import risk_summary
    assert risk_summary(None) == {"high": 0, "medium": 0, "low": 0, "total": 0}


@pytest.mark.django_db
def test_risk_summary_buckets(plant, user):
    from apps.reporting.services import risk_summary
    make_risk(plant, user, 5, 4)   # score 20 → high (>14)
    make_risk(plant, user, 2, 5)   # score 10 → medium (7<.<=14)
    make_risk(plant, user, 2, 2)   # score 4  → low (<=7)
    make_risk(plant, user, 3, 4, status="bozza")  # esclusa (non completato)

    out = risk_summary(str(plant.id))
    assert out == {"high": 1, "medium": 1, "low": 1, "total": 3}


@pytest.mark.django_db
def test_risk_summary_plant_filter(plant, other_plant, user):
    from apps.reporting.services import risk_summary
    make_risk(plant, user, 5, 4)
    make_risk(other_plant, user, 5, 4)
    assert risk_summary(str(plant.id))["total"] == 1
    assert risk_summary(None)["total"] == 2


# ───────────────────────────────────────────────────────────────────────────
# incident_summary
# ───────────────────────────────────────────────────────────────────────────
def make_incident(plant, user, severity="alta", status="aperto", **extra):
    from apps.incidents.models import Incident
    return Incident.objects.create(
        plant=plant,
        title=extra.pop("title", "Inc"),
        description="d",
        detected_at=timezone.now(),
        severity=severity,
        status=status,
        nis2_notifiable=extra.pop("nis2_notifiable", "no"),
        created_by=user,
        **extra,
    )


@pytest.mark.django_db
def test_incident_summary_breakdowns(plant, user):
    from apps.reporting.services import incident_summary
    make_incident(plant, user, severity="alta", status="aperto")
    make_incident(plant, user, severity="alta", status="chiuso")
    make_incident(plant, user, severity="bassa", status="aperto")

    out = incident_summary(str(plant.id))
    assert out["total"] == 3
    assert out["by_severity"] == {"alta": 2, "bassa": 1}
    assert out["by_status"]["aperto"] == 2
    assert out["by_status"]["chiuso"] == 1


@pytest.mark.django_db
def test_incident_summary_plant_filter(plant, other_plant, user):
    from apps.reporting.services import incident_summary
    make_incident(plant, user)
    make_incident(other_plant, user)
    assert incident_summary(str(plant.id))["total"] == 1
    assert incident_summary(None)["total"] == 2


# ───────────────────────────────────────────────────────────────────────────
# compliance_summary
# ───────────────────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_compliance_summary_no_plant():
    from apps.reporting.services import compliance_summary
    assert compliance_summary(None) == {"total": 0, "by_status": {}, "pct_compliant": 0}


# ───────────────────────────────────────────────────────────────────────────
# dashboard_summary
# ───────────────────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_dashboard_summary_no_plant_counts_active_plants(plant, other_plant):
    from apps.reporting.services import dashboard_summary
    out = dashboard_summary(None)
    assert out["plants_active"] == 2
    assert out["frameworks"] == []
    assert out["vacant_roles"] == []


@pytest.mark.django_db
def test_dashboard_summary_risk_and_incident_counts(plant, user):
    from apps.reporting.services import dashboard_summary
    make_risk(plant, user, 5, 4)            # red
    make_risk(plant, user, 2, 5)            # yellow
    make_incident(plant, user, status="aperto", nis2_notifiable="si")
    make_incident(plant, user, status="in_analisi")
    make_incident(plant, user, status="chiuso")  # non aperto/in_analisi → escluso

    out = dashboard_summary(str(plant.id))
    assert out["risks_red"] == 1
    assert out["risks_yellow"] == 1
    assert out["incidents_open"] == 2
    assert out["incidents_nis2"] == 1
    assert out["plant_id"] == str(plant.id)


@pytest.mark.django_db
def test_dashboard_summary_overdue_tasks(plant, user):
    from apps.reporting.services import dashboard_summary
    from apps.tasks.models import Task
    today = timezone.localdate()
    Task.objects.create(plant=plant, title="late", status="aperto",
                        due_date=today - timedelta(days=2), created_by=user)
    Task.objects.create(plant=plant, title="future", status="aperto",
                        due_date=today + timedelta(days=5), created_by=user)
    Task.objects.create(plant=plant, title="done", status="completato",
                        due_date=today - timedelta(days=2), created_by=user)
    assert dashboard_summary(str(plant.id))["tasks_overdue"] == 1


# ───────────────────────────────────────────────────────────────────────────
# kpi_trend
# ───────────────────────────────────────────────────────────────────────────
def make_snapshot(plant, week_start, framework="ISO27001", **extra):
    from apps.reporting.models import IsmsKpiSnapshot
    return IsmsKpiSnapshot.objects.create(
        plant=plant, week_start=week_start, framework_code=framework, **extra
    )


@pytest.mark.django_db
def test_kpi_trend_orders_and_filters_framework(plant):
    from apps.reporting.services import kpi_trend
    base = timezone.localdate()
    make_snapshot(plant, base - timedelta(days=14), pct_compliant=50.0)
    make_snapshot(plant, base - timedelta(days=7), pct_compliant=60.0)
    make_snapshot(plant, base, framework="NIS2", pct_compliant=99.0)

    out = kpi_trend(str(plant.id), "ISO27001", 12)
    assert out["framework"] == "ISO27001"
    assert len(out["results"]) == 2
    # ordinati per week_start crescente
    assert out["results"][0]["pct_compliant"] == 50.0
    assert out["results"][1]["pct_compliant"] == 60.0


@pytest.mark.django_db
def test_kpi_trend_org_wide_only_when_no_plant(plant):
    from apps.reporting.services import kpi_trend
    base = timezone.localdate()
    make_snapshot(plant, base, pct_compliant=10.0)            # plant-specific
    make_snapshot(None, base, pct_compliant=20.0)             # org-wide
    out = kpi_trend(None, "ISO27001", 12)
    assert len(out["results"]) == 1
    assert out["results"][0]["pct_compliant"] == 20.0


@pytest.mark.django_db
def test_kpi_trend_weeks_clamped():
    from apps.reporting.services import kpi_trend
    assert kpi_trend(None, "ISO27001", 0)  # non solleva (clamp a 1)
    # input non numerico → default 12, comunque valido
    assert kpi_trend(None, "ISO27001", "abc")["framework"] == "ISO27001"


# ───────────────────────────────────────────────────────────────────────────
# owner_report
# ───────────────────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_owner_report_risks_by_owner(plant, user):
    from apps.reporting.services import owner_report
    make_risk(plant, user, 5, 4, owner=user)   # red
    make_risk(plant, user, 2, 2, owner=user)   # green

    out = owner_report(str(plant.id))
    assert len(out["risks_by_owner"]) == 1
    entry = out["risks_by_owner"][0]
    assert entry["totale"] == 2
    assert entry["rossi"] == 1
    assert entry["verdi"] == 1
    assert entry["owner_email"] == user.email


@pytest.mark.django_db
def test_owner_report_tasks_by_owner(plant, user):
    from apps.reporting.services import owner_report
    from apps.tasks.models import Task
    today = timezone.localdate()
    Task.objects.create(plant=plant, title="t1", status="aperto", assigned_to=user,
                        due_date=today - timedelta(days=1), created_by=user)
    Task.objects.create(plant=plant, title="t2", status="in_corso", assigned_to=user,
                        due_date=today + timedelta(days=3), created_by=user)

    out = owner_report(str(plant.id))
    tasks = out["tasks_by_owner"]
    assert len(tasks) == 1
    assert tasks[0]["aperti"] == 2
    assert tasks[0]["scaduti"] == 1


# ───────────────────────────────────────────────────────────────────────────
# risk_bia_bcp
# ───────────────────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_risk_bia_bcp_kpis(plant, user):
    from apps.reporting.services import risk_bia_bcp
    make_risk(plant, user, 5, 4)                                  # red
    make_risk(plant, user, 2, 5)                                  # yellow
    make_risk(plant, user, 5, 4, needs_revaluation=True)          # red + da rivalutare
    make_risk(plant, user, 2, 2, risk_accepted_formally=True)     # green + accettato

    out = risk_bia_bcp(str(plant.id))
    k = out["kpis"]
    assert k["risks_total"] == 4
    assert k["risks_red"] == 2
    assert k["risks_yellow"] == 1
    assert k["risks_needs_revaluation"] == 1
    assert k["risks_formally_accepted"] == 1


@pytest.mark.django_db
def test_risk_bia_bcp_heatmap(plant, user):
    from apps.reporting.services import risk_bia_bcp
    make_risk(plant, user, 3, 4)
    make_risk(plant, user, 3, 4)
    make_risk(plant, user, 1, 1)

    out = risk_bia_bcp(str(plant.id))
    assert len(out["heatmap"]) == 25  # griglia 5x5 completa
    cell = {(c["prob"], c["impact"]): c["count"] for c in out["heatmap"]}
    assert cell[(3, 4)] == 2
    assert cell[(1, 1)] == 1
    assert cell[(5, 5)] == 0


@pytest.mark.django_db
def test_risk_bia_bcp_top_risks_sorted(plant, user):
    from apps.reporting.services import risk_bia_bcp
    make_risk(plant, user, 2, 2, name="low")    # 4
    make_risk(plant, user, 5, 4, name="high")   # 20
    make_risk(plant, user, 2, 5, name="mid")    # 10

    top = risk_bia_bcp(str(plant.id))["top_risks"]
    assert [r["name"] for r in top] == ["high", "mid", "low"]
    assert top[0]["score"] == 20


@pytest.mark.django_db
def test_risk_bia_bcp_ale_total_coverage_and_top_risks(plant, user):
    """ALE: somma di portafoglio, copertura % e colonna sui top_risks.

    Un rischio collegato a una BIA con downtime_cost_hour valorizzato ha ALE > 0;
    uno senza processo critico vale 0 e abbassa la copertura."""
    from apps.bia.models import CriticalProcess
    from apps.reporting.services import risk_bia_bcp

    proc = CriticalProcess.objects.create(
        plant=plant, name="ProcALE", criticality=4, downtime_cost_hour=1000
    )
    # Residua: prob=3, impact=3 → ore_fermo=24, prob_annua=1.0 → 1000*24*1 = 24000.
    # Inerente (pre-controlli): inherent prob=4, impact=4 → 72h × 3.0/anno → 1000*72*3 = 216000.
    make_risk(
        plant, user, 3, 3, name="with_bia", critical_process=proc,
        inherent_probability=4, inherent_impact=4,
    )
    make_risk(plant, user, 5, 4, name="no_bia")  # nessuna BIA → ALE 0

    out = risk_bia_bcp(str(plant.id))
    k = out["kpis"]
    assert k["ale_total"] == 24000.0
    assert k["ale_total_inherent"] == 216000.0
    assert k["ale_saved"] == 192000.0          # rischio abbattuto dai controlli
    assert k["ale_saved_pct"] == 88.9
    assert k["ale_valued_count"] == 1
    assert k["ale_coverage_pct"] == 50.0

    row = {r["name"]: r for r in out["top_risks"]}
    assert row["with_bia"]["ale"] == 24000.0
    assert row["with_bia"]["ale_inherent"] == 216000.0
    assert row["no_bia"]["ale"] == 0
    assert row["no_bia"]["ale_inherent"] == 0


@pytest.mark.django_db
def test_risk_bia_bcp_treatment_rosi(plant, user):
    """ROSI: ALE evitata vs costo annualizzato (CapEx ammortizzato su 3 anni) + payback."""
    from apps.bia.models import CriticalProcess, TreatmentOption
    from apps.reporting.services import risk_bia_bcp

    proc = CriticalProcess.objects.create(
        plant=plant, name="ProcROSI", criticality=4, downtime_cost_hour=1000
    )
    # ALE residua processo: prob=3, impact=3 → 1000*24*1 = 24000.
    make_risk(plant, user, 3, 3, name="r_rosi", critical_process=proc)
    # Trattamento: abbatte il 50% → ALE evitata 12000/anno.
    # annual_cost = cost_annual 2000 + cost_implementation 12000 / 3 = 6000.
    # net = 12000-6000 = 6000 → ROSI 100%. payback = 12000 / (12000-2000) * 12 = 14.4 mesi.
    TreatmentOption.objects.create(
        process=proc, title="EDR", cost_implementation=12000,
        cost_annual=2000, ale_reduction_pct=50,
    )

    out = risk_bia_bcp(str(plant.id))
    tr = out["treatments"]
    assert len(tr) == 1
    row = tr[0]
    assert row["ale_avoided"] == 12000.0
    assert row["annual_cost"] == 6000.0
    assert row["net_annual"] == 6000.0
    assert row["rosi_pct"] == 100.0
    assert row["payback_months"] == 14.4
    assert row["worth_it"] is True

    tot = out["treatments_totals"]
    assert tot["count"] == 1
    assert tot["ale_avoided"] == 12000.0
    assert tot["annual_cost"] == 6000.0
    assert tot["rosi_pct"] == 100.0
    assert tot["amort_years"] == 3


@pytest.mark.django_db
def test_risk_bia_bcp_critical_no_bcp_and_test_overdue(plant, user):
    from apps.bcp.models import BcpPlan
    from apps.bia.models import CriticalProcess
    from apps.reporting.services import risk_bia_bcp
    today = timezone.localdate()

    # Processo critico con BCP approvato ma test scaduto
    p1 = CriticalProcess.objects.create(plant=plant, name="P1", criticality=5)
    BcpPlan.objects.create(plant=plant, title="B1", status="approvato",
                          critical_process=p1, next_test_date=today - timedelta(days=10),
                          created_by=user)
    # Processo critico SENZA alcun BCP
    CriticalProcess.objects.create(plant=plant, name="P2", criticality=5)

    out = risk_bia_bcp(str(plant.id))
    assert out["kpis"]["bia_critical_no_bcp"] == 1   # solo P2
    assert out["kpis"]["bcp_test_overdue"] == 1      # B1 scaduto


@pytest.mark.django_db
def test_risk_bia_bcp_table_best_plan_and_last_test(plant, user):
    from apps.bcp.models import BcpPlan, BcpTest
    from apps.bia.models import CriticalProcess
    from apps.reporting.services import risk_bia_bcp
    today = timezone.localdate()

    proc = CriticalProcess.objects.create(plant=plant, name="ProcX", criticality=4)
    # piano approvato (preferito) con un test
    approved = BcpPlan.objects.create(plant=plant, title="approved", status="approvato",
                                     critical_process=proc, next_test_date=today + timedelta(days=30),
                                     created_by=user)
    BcpPlan.objects.create(plant=plant, title="draft", status="bozza",
                          critical_process=proc, created_by=user)
    BcpTest.objects.create(plan=approved, test_date=today - timedelta(days=5),
                          result="superato", created_by=user)

    table = risk_bia_bcp(str(plant.id))["bia_bcp_table"]
    row = next(r for r in table if r["process_name"] == "ProcX")
    assert row["bcp_plans_count"] == 2
    assert row["bcp_status"] == "approvato"           # approvato batte bozza
    assert row["last_test_result"] == "superato"
    assert row["test_overdue"] is False               # next_test futuro


# ───────────────────────────────────────────────────────────────────────────
# kpi_overview → _mttr (incl. regressione bug major/minor) e _supplier_nda
# ───────────────────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_mttr_findings_major_minor_mapping(plant, user):
    """Regressione: prima la view filtrava finding_type='major'/'minor' (codici
    reali: major_nc/minor_nc) → MTTR sempre 0 per quelle voci. Ora conta."""
    from apps.audit_prep.models import AuditFinding, AuditPrep
    from apps.reporting.services import _mttr
    now = timezone.now()

    prep = AuditPrep.objects.create(plant=plant, title="Prep", created_by=user)
    AuditFinding.objects.create(
        audit_prep=prep, finding_type="major_nc", title="MJ", description="d",
        audit_date=now.date() - timedelta(days=10),
        closed_at=now, created_by=user,
    )
    # forziamo created_at ~5 giorni prima della chiusura per un avg_days sensato
    AuditFinding.objects.filter(audit_prep=prep).update(
        created_at=now - timedelta(days=5)
    )

    out = _mttr(str(plant.id))
    assert out["findings"]["major"]["count"] == 1
    assert out["findings"]["major"]["avg_days"] is not None
    assert out["findings"]["minor"]["count"] == 0
    assert out["findings"]["all"]["count"] == 1


@pytest.mark.django_db
def test_supplier_nda_statuses(plant, user):
    from apps.documents.models import Document
    from apps.reporting.services import _supplier_nda
    from apps.suppliers.models import Supplier
    today = timezone.localdate()

    def nda(supplier, expiry):
        Document.objects.create(
            title=f"NDA {supplier.name}", document_type="contratto", status="approvato",
            supplier=supplier, expiry_date=expiry, created_by=user,
        )

    s_ok = Supplier.objects.create(name="OK", status="attivo", created_by=user)
    nda(s_ok, today + timedelta(days=200))
    s_exp = Supplier.objects.create(name="Expiring", status="attivo", created_by=user)
    nda(s_exp, today + timedelta(days=30))
    s_old = Supplier.objects.create(name="Expired", status="attivo", created_by=user)
    nda(s_old, today - timedelta(days=5))
    Supplier.objects.create(name="NoNda", status="attivo", created_by=user)

    out = _supplier_nda(None)
    assert out["total"] == 4
    assert out["covered"] == 3        # ok + expiring + expired hanno NDA approvato
    assert out["expiring_soon"] == 1
    assert out["expired"] == 1
    assert out["without_nda"] == 1
    statuses = {d["name"]: d["nda_status"] for d in out["suppliers"]}
    assert statuses == {"OK": "ok", "Expiring": "expiring", "Expired": "expired", "NoNda": "missing"}


@pytest.mark.django_db
def test_kpi_overview_shape(plant, user):
    from apps.reporting.services import kpi_overview
    out = kpi_overview(str(plant.id))
    assert set(out.keys()) == {"required_docs", "mttr", "training", "supplier_nda"}
    assert isinstance(out["required_docs"], list)
    assert "findings" in out["mttr"]


@pytest.mark.django_db
def test_kpi_trend_returns_most_recent_weeks(plant):
    """Con più settimane del limite deve mostrare le ultime, non le prime."""
    from apps.reporting.services import kpi_trend
    base = timezone.localdate()
    for i in range(5):
        make_snapshot(plant, base - timedelta(days=7 * i), pct_compliant=float(i))

    out = kpi_trend(str(plant.id), "ISO27001", 3)
    weeks = [r["week_start"] for r in out["results"]]
    assert weeks == [base - timedelta(days=14), base - timedelta(days=7), base]


# ───────────────────────────────────────────────────────────────────────────
# generate_weekly_kpi_snapshots
# ───────────────────────────────────────────────────────────────────────────
def _framework_with_instance(code, plant, user, status="compliant", active=True):
    from apps.controls.models import Control, ControlInstance, Framework
    from apps.plants.models import PlantFramework
    fw = Framework.objects.filter(code=code).first() or Framework.objects.create(
        code=code, name=code, version="1", published_at=timezone.localdate(),
    )
    control = Control.objects.create(
        framework=fw, external_id=f"{code}-{plant.code}",
        translations={"it": {"title": code}}, evidence_requirement={},
    )
    ControlInstance.objects.create(plant=plant, control=control, status=status, created_by=user)
    PlantFramework.objects.create(
        plant=plant, framework=fw, active_from=timezone.localdate(), active=active,
    )
    return fw


@pytest.mark.django_db
def test_weekly_snapshot_only_active_frameworks_per_plant(plant, other_plant, user):
    from apps.reporting.models import IsmsKpiSnapshot
    from apps.reporting.tasks import generate_weekly_kpi_snapshots
    _framework_with_instance("ISO27001", plant, user)
    _framework_with_instance("NIS2", other_plant, user)
    # TISAX con istanze sul sito ma disattivato: nessuna serie
    _framework_with_instance("TISAX_L2", plant, user, active=False)

    generate_weekly_kpi_snapshots()

    per_plant = set(
        IsmsKpiSnapshot.objects.exclude(plant=None).values_list("plant__code", "framework_code")
    )
    assert per_plant == {("REP-A", "ISO27001"), ("REP-B", "NIS2")}
    org = set(IsmsKpiSnapshot.objects.filter(plant=None).values_list("framework_code", flat=True))
    assert org == {"ISO27001", "NIS2"}


@pytest.mark.django_db
def test_weekly_snapshot_org_wide_counts_only_plants_with_framework_active(plant, other_plant, user):
    from apps.reporting.models import IsmsKpiSnapshot
    from apps.reporting.tasks import generate_weekly_kpi_snapshots
    _framework_with_instance("ISO27001", plant, user, status="compliant")
    # stesso framework con istanza in gap su un sito dove è disattivato
    _framework_with_instance("ISO27001", other_plant, user, status="gap", active=False)

    generate_weekly_kpi_snapshots()

    org = IsmsKpiSnapshot.objects.get(plant=None, framework_code="ISO27001")
    assert org.controls_total == 1
    assert org.controls_gap == 0
    assert org.pct_compliant == 100.0


@pytest.mark.django_db
def test_weekly_snapshot_counts_critical_incidents(plant, user):
    from apps.reporting.models import IsmsKpiSnapshot
    from apps.reporting.tasks import generate_weekly_kpi_snapshots
    _framework_with_instance("ISO27001", plant, user)
    make_incident(plant, user, severity="critica")
    make_incident(plant, user, severity="alta")

    generate_weekly_kpi_snapshots()

    snap = IsmsKpiSnapshot.objects.get(plant=plant, framework_code="ISO27001")
    assert snap.open_incidents == 2
    assert snap.critical_incidents == 1


# ───────────────────────────────────────────────────────────────────────────
# risk_bia_bcp — propensione al rischio e copertura BCP
# ───────────────────────────────────────────────────────────────────────────
def _appetite(plant=None, score=14, max_red=3):
    from apps.risk.models import RiskAppetitePolicy
    return RiskAppetitePolicy.objects.create(
        plant=plant, max_acceptable_score=score, max_red_risks_count=max_red,
        valid_from=timezone.localdate() - timedelta(days=1),
    )


@pytest.mark.django_db
def test_risk_over_appetite_uses_site_policy(plant, other_plant, user):
    from apps.reporting.services import risk_bia_bcp
    _appetite(None, score=14)          # organizzazione
    _appetite(plant, score=9)          # sito A più severo
    make_risk(plant, user, 2, 5)       # 10: oltre la soglia del sito A (9)
    make_risk(plant, user, 2, 4)       # 8: sotto
    make_risk(other_plant, user, 3, 4)  # 12: sotto la soglia di organizzazione (14)
    make_risk(other_plant, user, 3, 5)  # 15: oltre

    site = risk_bia_bcp(str(plant.id))
    assert site["kpis"]["risks_over_appetite"] == 1
    assert site["appetite"]["max_acceptable_score"] == 9
    assert site["appetite"]["defined"] is True
    assert [r["over_appetite"] for r in site["top_risks"]] == [True, False]

    org = risk_bia_bcp(None)
    assert org["kpis"]["risks_over_appetite"] == 2
    assert org["appetite"]["max_acceptable_score"] == 14
    assert org["appetite"]["per_plant"] is True


@pytest.mark.django_db
def test_risk_appetite_default_when_no_policy(plant, user):
    from apps.reporting.services import DEFAULT_APPETITE_SCORE, risk_bia_bcp
    make_risk(plant, user, 3, 5)  # 15
    out = risk_bia_bcp(str(plant.id))
    assert out["appetite"]["defined"] is False
    assert out["appetite"]["max_acceptable_score"] == DEFAULT_APPETITE_SCORE
    assert out["kpis"]["risks_over_appetite"] == 1


@pytest.mark.django_db
def test_bcp_coverage_only_approved_and_m2m_link(plant, user):
    """Copre solo un piano approvato, anche se collegato dall'elenco processi
    (M2M); bozze e archiviati non coprono e non contano come test da fare."""
    from apps.bcp.models import BcpPlan
    from apps.bia.models import CriticalProcess
    from apps.reporting.services import risk_bia_bcp
    today = timezone.localdate()

    via_m2m = CriticalProcess.objects.create(plant=plant, name="M2M", criticality=5)
    plan = BcpPlan.objects.create(plant=plant, title="Approvato M2M", status="approvato",
                                  next_test_date=today + timedelta(days=30), created_by=user)
    plan.critical_processes.add(via_m2m)

    only_draft = CriticalProcess.objects.create(plant=plant, name="Bozza", criticality=4)
    BcpPlan.objects.create(plant=plant, title="Draft", status="bozza",
                           critical_process=only_draft, created_by=user)
    only_archived = CriticalProcess.objects.create(plant=plant, name="Archiviato", criticality=4)
    BcpPlan.objects.create(plant=plant, title="Old", status="archiviato",
                           critical_process=only_archived, next_test_date=today - timedelta(days=90),
                           created_by=user)

    out = risk_bia_bcp(str(plant.id))
    assert out["kpis"]["bia_critical_no_bcp"] == 2      # Bozza + Archiviato
    assert out["kpis"]["bcp_test_overdue"] == 0         # bozza/archiviato non contano
    rows = {r["process_name"]: r for r in out["bia_bcp_table"]}
    assert rows["M2M"]["bcp_status"] == "approvato"
    assert rows["Bozza"]["bcp_status"] == "bozza"
    assert rows["Bozza"]["test_overdue"] is False
    assert rows["Archiviato"]["bcp_status"] is None


@pytest.mark.django_db
def test_required_docs_no_fallback_to_controls(plant, user):
    """Senza documenti obbligatori configurati la riga lo dice, a zero: niente
    stato dei controlli al posto della copertura documentale."""
    from apps.controls.models import Control, ControlInstance, Framework
    from apps.plants.models import PlantFramework
    from apps.reporting.services import kpi_overview
    fw = Framework.objects.create(code="FWX", name="Framework X", version="1", published_at=timezone.localdate())
    PlantFramework.objects.create(plant=plant, framework=fw, active_from=timezone.localdate())
    c = Control.objects.create(framework=fw, external_id="X1", translations={}, evidence_requirement={})
    ControlInstance.objects.create(plant=plant, control=c, status="compliant", created_by=user)

    docs = kpi_overview(str(plant.id))["required_docs"]
    row = next(r for r in docs if r["framework"] == "FWX")
    assert row["no_required_docs"] is True
    assert row["framework_name"] == "Framework X"
    assert (row["total"], row["green"], row["pct_coverage"]) == (0, 0, 0)
    # la copertura documentale è per sito: senza sito non c'è
    assert kpi_overview(None)["required_docs"] is None

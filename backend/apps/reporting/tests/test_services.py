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

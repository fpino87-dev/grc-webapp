"""
Connettori KPI di continuità operativa (M16 BCP/DR).

I test di continuità sono eventi rari: questi KPI misurano lo STATO
(anzianità, esito, scostamento dagli obiettivi), non la quantità nel periodo.
"""
import datetime

import pytest
from django.utils import timezone


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="DR-P", name="Plant DR", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def other_plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="DR-P2", name="Plant DR 2", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


def _monday():
    from apps.tasks.services import _monday_of
    return _monday_of(timezone.localdate())


def _plan(plant, **kwargs):
    from apps.bcp.models import BcpPlan
    kwargs.setdefault("title", "Piano DR datacenter")
    kwargs.setdefault("status", "approvato")
    return BcpPlan.objects.create(plant=plant, **kwargs)


def _test(plan, days_ago=10, result="superato", **kwargs):
    from apps.bcp.models import BcpTest
    return BcpTest.objects.create(
        plan=plan,
        test_date=timezone.localdate() - datetime.timedelta(days=days_ago),
        result=result,
        **kwargs,
    )


def _process(plant, **kwargs):
    from apps.bia.models import CriticalProcess
    kwargs.setdefault("name", "Produzione linea 1")
    kwargs.setdefault("status", "approvato")
    return CriticalProcess.objects.create(plant=plant, **kwargs)


# ── Anzianità dell'ultimo test ───────────────────────────────────────────────

@pytest.mark.django_db
def test_age_takes_the_worst_plant_not_the_average(plant):
    """Un piano trascurato non deve essere mascherato dagli altri in regola."""
    from apps.tasks.kpi_connectors import dr_test_age_days

    _plan(plant, title="Recente", last_test_date=timezone.localdate() - datetime.timedelta(days=10))
    _plan(plant, title="Trascurato", last_test_date=timezone.localdate() - datetime.timedelta(days=400))

    res = dr_test_age_days(plant, _monday())
    assert res["value"] == 400.0
    assert "Trascurato" in res["note"]


@pytest.mark.django_db
def test_never_tested_plan_counts_from_creation(plant):
    """Un piano mai testato non deve sparire dal conteggio proprio perché non
    è mai stato provato."""
    from apps.tasks.kpi_connectors import dr_test_age_days

    _plan(plant, title="Mai testato", last_test_date=None)
    res = dr_test_age_days(plant, _monday())
    assert res["value"] is not None
    assert "mai testati" in res["note"]


@pytest.mark.django_db
def test_age_ignores_draft_and_archived_plans(plant):
    from apps.tasks.kpi_connectors import dr_test_age_days

    _plan(plant, title="Bozza", status="bozza",
          last_test_date=timezone.localdate() - datetime.timedelta(days=900))
    _plan(plant, title="Attivo", last_test_date=timezone.localdate() - datetime.timedelta(days=30))
    assert dr_test_age_days(plant, _monday())["value"] == 30.0


@pytest.mark.django_db
def test_age_is_scoped_to_the_plant(plant, other_plant):
    from apps.tasks.kpi_connectors import dr_test_age_days

    _plan(plant, last_test_date=timezone.localdate() - datetime.timedelta(days=20))
    _plan(other_plant, last_test_date=timezone.localdate() - datetime.timedelta(days=800))
    assert dr_test_age_days(plant, _monday())["value"] == 20.0


@pytest.mark.django_db
def test_age_without_plans_is_no_data(plant):
    from apps.tasks.kpi_connectors import dr_test_age_days

    res = dr_test_age_days(plant, _monday())
    assert res["value"] is None
    assert "Nessun piano" in res["note"]


# ── Esito dei test ───────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_partial_result_does_not_count_as_passed(plant):
    from apps.tasks.kpi_connectors import dr_test_pass_rate

    plan = _plan(plant)
    _test(plan, days_ago=30, result="superato")
    _test(plan, days_ago=60, result="parziale")
    _test(plan, days_ago=90, result="fallito")
    res = dr_test_pass_rate(plant, _monday())
    assert res["value"] == 33.33
    assert res["run_count"] == 3


@pytest.mark.django_db
def test_pass_rate_ignores_tests_older_than_a_year(plant):
    from apps.tasks.kpi_connectors import dr_test_pass_rate

    plan = _plan(plant)
    _test(plan, days_ago=400, result="fallito")
    _test(plan, days_ago=100, result="superato")
    assert dr_test_pass_rate(plant, _monday())["value"] == 100.0


@pytest.mark.django_db
def test_pass_rate_without_recent_tests_is_no_data(plant):
    from apps.tasks.kpi_connectors import dr_test_pass_rate

    _plan(plant)
    assert dr_test_pass_rate(plant, _monday())["value"] is None


# ── Scostamento RTO ──────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_rto_gap_is_positive_when_recovery_is_slower_than_promised(plant):
    from apps.tasks.kpi_connectors import dr_rto_gap_hours

    plan = _plan(plant, rto_hours=4)
    _test(plan, days_ago=30, rto_achieved_hours=30)
    res = dr_rto_gap_hours(plant, _monday())
    assert res["value"] == 26.0
    assert "peggiore 26h" in res["note"]


@pytest.mark.django_db
def test_rto_gap_is_negative_when_recovery_beats_the_target(plant):
    from apps.tasks.kpi_connectors import dr_rto_gap_hours

    plan = _plan(plant, rto_hours=8)
    _test(plan, days_ago=10, rto_achieved_hours=6)
    assert dr_rto_gap_hours(plant, _monday())["value"] == -2.0


@pytest.mark.django_db
def test_rto_gap_skips_tests_without_measurement(plant):
    from apps.tasks.kpi_connectors import dr_rto_gap_hours

    plan = _plan(plant, rto_hours=4)
    _test(plan, days_ago=20, rto_achieved_hours=None)
    res = dr_rto_gap_hours(plant, _monday())
    assert res["value"] is None
    assert "RTO misurato" in res["note"]


# ── Piani con test scaduto ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_overdue_counts_expired_and_never_tested(plant):
    from apps.tasks.kpi_connectors import dr_plans_overdue_count

    _plan(plant, title="Scaduto",
          last_test_date=timezone.localdate() - datetime.timedelta(days=400),
          next_test_date=timezone.localdate() - datetime.timedelta(days=35))
    _plan(plant, title="Mai testato", last_test_date=None)
    _plan(plant, title="In regola",
          last_test_date=timezone.localdate() - datetime.timedelta(days=10),
          next_test_date=timezone.localdate() + datetime.timedelta(days=355))

    res = dr_plans_overdue_count(plant, _monday())
    assert res["value"] == 2.0
    assert res["run_count"] == 3


# ── Copertura BIA ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_coverage_finds_uncovered_critical_processes(plant):
    from apps.tasks.kpi_connectors import bcp_critical_process_coverage

    covered = _process(plant, name="Coperto")
    _process(plant, name="Scoperto")
    plan = _plan(plant)
    plan.critical_processes.add(covered)

    res = bcp_critical_process_coverage(plant, _monday())
    assert res["value"] == 50.0
    assert "1/2" in res["note"]


@pytest.mark.django_db
def test_coverage_accepts_the_legacy_single_process_link(plant):
    """Il collegamento storico via FK singola vale quanto quello M2M."""
    from apps.tasks.kpi_connectors import bcp_critical_process_coverage

    process = _process(plant)
    _plan(plant, critical_process=process)
    assert bcp_critical_process_coverage(plant, _monday())["value"] == 100.0


@pytest.mark.django_db
def test_coverage_ignores_draft_processes(plant):
    from apps.tasks.kpi_connectors import bcp_critical_process_coverage

    _process(plant, name="Bozza", status="bozza")
    res = bcp_critical_process_coverage(plant, _monday())
    assert res["value"] is None


# ── RTO del piano vs target BIA ──────────────────────────────────────────────

@pytest.mark.django_db
def test_plan_promising_less_than_the_bia_target_is_counted_out(plant):
    from apps.tasks.kpi_connectors import bcp_rto_meets_bia_target_rate

    strict = _process(plant, name="Severo", rto_target_hours=4)
    loose = _process(plant, name="Tollerante", rto_target_hours=48)

    ok_plan = _plan(plant, title="Rispetta", rto_hours=24)
    ok_plan.critical_processes.add(loose)
    ko_plan = _plan(plant, title="Non rispetta", rto_hours=24)
    ko_plan.critical_processes.add(strict)

    res = bcp_rto_meets_bia_target_rate(plant, _monday())
    assert res["value"] == 50.0


@pytest.mark.django_db
def test_strictest_target_wins_when_a_plan_covers_several_processes(plant):
    from apps.tasks.kpi_connectors import bcp_rto_meets_bia_target_rate

    plan = _plan(plant, rto_hours=12)
    plan.critical_processes.add(_process(plant, name="A", rto_target_hours=24))
    plan.critical_processes.add(_process(plant, name="B", rto_target_hours=8))

    assert bcp_rto_meets_bia_target_rate(plant, _monday())["value"] == 0.0


@pytest.mark.django_db
def test_plans_without_a_bia_target_are_not_judged(plant):
    from apps.tasks.kpi_connectors import bcp_rto_meets_bia_target_rate

    plan = _plan(plant, rto_hours=12)
    plan.critical_processes.add(_process(plant, rto_target_hours=None))
    assert bcp_rto_meets_bia_target_rate(plant, _monday())["value"] is None


# ── Integrazione col motore ──────────────────────────────────────────────────

@pytest.mark.django_db
def test_dr_kpi_is_stored_as_a_snapshot(plant):
    from apps.tasks.models import KPIDefinition
    from apps.tasks.services import compute_and_store_kpi_snapshot

    _plan(plant, last_test_date=timezone.localdate() - datetime.timedelta(days=400))
    kpi = KPIDefinition.objects.create(
        kpi_code="dr_test_age_days", name="Anzianità ultimo test DR", unit="giorni",
        source="internal", aggregation="last_value", plant=plant,
        threshold_warning=365.0, threshold_critical=540.0, threshold_direction="below",
    )
    snap = compute_and_store_kpi_snapshot(kpi, plant, _monday())
    assert snap.value == 400.0
    assert snap.status == "warning"   # oltre 365 giorni, sotto 540
    assert snap.source == "internal"


@pytest.mark.django_db
def test_dr_kpis_are_suggested_only_with_matching_frameworks(plant):
    """I 6 KPI di continuità entrano nel wizard per i framework che li marcano."""
    from apps.reporting.services import kpi_suggest

    codes = {s["kpi_code"] for s in kpi_suggest(str(plant.id), "it")["suggestions"]}
    assert {
        "dr_test_age_days", "dr_test_pass_rate", "dr_rto_gap_hours",
        "dr_plans_overdue_count", "bcp_critical_process_coverage",
        "bcp_rto_meets_bia_target_rate",
    } <= codes

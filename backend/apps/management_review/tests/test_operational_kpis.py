"""P2-4 — catena KPI engine → revisione direzione.

Verifica che `get_operational_kpi_summary` aggreghi correttamente l'ultimo
snapshot di ogni KPI operativo rilevante per il plant, e che lo snapshot venga
incorporato in `get_kpi_snapshot` / persistito da `complete_review`.
"""
import datetime

import pytest
from django.contrib.auth import get_user_model

from apps.management_review.models import ManagementReview
from apps.management_review.services import (
    complete_review,
    get_kpi_snapshot,
    get_operational_kpi_summary,
)
from apps.plants.models import Plant
from apps.tasks.models import KPIDefinition, OperationalKpiSnapshot

User = get_user_model()
pytestmark = pytest.mark.django_db

W1 = datetime.date(2026, 5, 18)   # lunedì
W2 = datetime.date(2026, 5, 25)   # lunedì successivo


@pytest.fixture
def plant(db):
    return Plant.objects.create(
        code="MRK-P", name="Plant KPI", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def other_plant(db):
    return Plant.objects.create(
        code="MRK-O", name="Altro Plant", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


def _kpi(code, plant=None, active=True, **kw):
    return KPIDefinition.objects.create(
        kpi_code=code, name=kw.get("name", code), unit=kw.get("unit", "%"),
        source="checklist", aggregation="success_rate", plant=plant,
        threshold_warning=kw.get("tw", 90), threshold_critical=kw.get("tc", 80),
        threshold_direction="above", is_active=active,
    )


def _snap(kpi, plant, week, value, status):
    return OperationalKpiSnapshot.objects.create(
        kpi_definition=kpi, plant=plant, week_start=week,
        value=value, status=status, source="checklist",
    )


def test_summary_includes_plant_specific_kpi(plant):
    kpi = _kpi("backup_success_rate", plant=plant)
    _snap(kpi, plant, W1, 95.0, "ok")
    summary = get_operational_kpi_summary(plant.id)
    assert summary["count"] == 1
    item = summary["items"][0]
    assert item["kpi_code"] == "backup_success_rate"
    assert item["value"] == 95.0
    assert item["status"] == "ok"
    assert item["scope"] == "plant"
    assert item["threshold_warning"] == 90


def test_summary_includes_global_kpi_with_per_plant_snapshot(plant):
    kpi = _kpi("vuln_open", plant=None)        # KPI globale
    _snap(kpi, plant, W1, 70.0, "warning")     # snapshot per-plant prodotto dal compute
    summary = get_operational_kpi_summary(plant.id)
    assert summary["count"] == 1
    assert summary["items"][0]["status"] == "warning"


def test_summary_includes_global_kpi_with_null_plant_snapshot(plant):
    kpi = _kpi("org_training", plant=None)
    _snap(kpi, None, W1, 60.0, "critical")     # snapshot globale (ingest API)
    summary = get_operational_kpi_summary(plant.id)
    assert summary["count"] == 1
    assert summary["items"][0]["scope"] == "global"


def test_summary_keeps_only_latest_week(plant):
    kpi = _kpi("backup_success_rate", plant=plant)
    _snap(kpi, plant, W1, 80.0, "critical")
    _snap(kpi, plant, W2, 96.0, "ok")
    summary = get_operational_kpi_summary(plant.id)
    assert summary["count"] == 1
    assert summary["items"][0]["value"] == 96.0   # W2, il più recente
    assert summary["items"][0]["week_start"] == W2.isoformat()


def test_summary_status_counts_and_attention(plant):
    _snap(_kpi("k_ok", plant=plant), plant, W1, 99, "ok")
    _snap(_kpi("k_warn", plant=plant), plant, W1, 85, "warning")
    _snap(_kpi("k_crit", plant=plant), plant, W1, 70, "critical")
    summary = get_operational_kpi_summary(plant.id)
    assert summary["count"] == 3
    assert summary["status_counts"] == {"ok": 1, "warning": 1, "critical": 1, "no_data": 0}
    assert summary["attention"] == 2


def test_summary_excludes_inactive_kpi(plant):
    kpi = _kpi("dismesso", plant=plant, active=False)
    _snap(kpi, plant, W1, 50, "critical")
    assert get_operational_kpi_summary(plant.id)["count"] == 0


def test_summary_excludes_other_plant_snapshot(plant, other_plant):
    kpi = _kpi("backup_success_rate", plant=other_plant)
    _snap(kpi, other_plant, W1, 95, "ok")
    assert get_operational_kpi_summary(plant.id)["count"] == 0


def test_summary_items_sorted_by_code(plant):
    _snap(_kpi("zzz", plant=plant), plant, W1, 99, "ok")
    _snap(_kpi("aaa", plant=plant), plant, W1, 99, "ok")
    codes = [i["kpi_code"] for i in get_operational_kpi_summary(plant.id)["items"]]
    assert codes == ["aaa", "zzz"]


def test_get_kpi_snapshot_embeds_operational_kpis(plant):
    kpi = _kpi("backup_success_rate", plant=plant)
    _snap(kpi, plant, W1, 95, "ok")
    snap = get_kpi_snapshot(plant.id)
    assert "operational_kpis" in snap
    assert snap["operational_kpis"]["count"] == 1


def test_complete_review_persists_operational_kpis(plant):
    user = User.objects.create_user(username="mr", email="mr@t.com", password="x")
    kpi = _kpi("backup_success_rate", plant=plant)
    _snap(kpi, plant, W1, 88, "warning")
    review = ManagementReview.objects.create(
        plant=plant, title="Q2 2026", review_date=W2, status="pianificato",
        created_by=user,
    )
    complete_review(review, user)
    review.refresh_from_db()
    assert review.status == "completato"
    ops = review.kpi_snapshot["operational_kpis"]
    assert ops["count"] == 1
    assert ops["attention"] == 1

"""KPI operativi — snapshot fuori scope (definizione disattivata/cancellata,
cambio globale → sito) ripuliti e mai mostrati al posto del valore reale."""
import datetime
import importlib

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.management_review.services import get_operational_kpi_summary
from apps.plants.models import Plant
from apps.tasks.kpi_scope import current_scope, sync_snapshots_with_scope
from apps.tasks.models import KPIDefinition, OperationalKpiSnapshot

User = get_user_model()
pytestmark = pytest.mark.django_db

KPI_DEF_URL = "/api/v1/tasks/kpi-definitions/"
W1 = datetime.date(2026, 9, 14)
W2 = datetime.date(2026, 9, 21)


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess

    u = User.objects.create_user(username="kpi_scope", email="kpi_scope@test.com", password="x", is_staff=True)
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _plant(code):
    return Plant.objects.create(code=code, name=f"Plant {code}", country="IT",
                                nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def pl(db):
    return _plant("KS-PL")


@pytest.fixture
def tn(db):
    return _plant("KS-TN")


def _def(code="dr_test_age_days", plant=None, active=True, source="internal"):
    return KPIDefinition.objects.create(
        kpi_code=code, name=code, unit="gg", source=source, aggregation="success_rate",
        plant=plant, threshold_warning=200, threshold_critical=365,
        threshold_direction="below", is_active=active,
    )


def _snap(kpi, plant, week, value, status):
    return OperationalKpiSnapshot.objects.create(
        kpi_definition=kpi, plant=plant, week_start=week, value=value, status=status, source=kpi.source,
    )


def _live(kpi, plant="any"):
    qs = OperationalKpiSnapshot.objects.filter(kpi_definition=kpi)
    return qs if plant == "any" else qs.filter(plant=plant)


# ── Scope ────────────────────────────────────────────────────────────────────

def test_scope_rules(pl, tn):
    glob = _def()
    site = _def(plant=pl)
    off = _def(code="other", active=False)
    scope = current_scope()
    assert scope[site.pk] == {pl.pk}
    assert pl.pk not in scope[glob.pk] and tn.pk in scope[glob.pk] and None in scope[glob.pk]
    assert scope[off.pk] == set()


# ── Caso reale: globale → per sito ───────────────────────────────────────────

def test_global_to_site_override_prunes_ghosts_keeps_legit(client, pl, tn):
    glob = _def()
    _snap(glob, pl, W1, None, "no_data")      # misurato quando PL usava la globale
    _snap(glob, tn, W1, 40, "ok")
    _snap(glob, None, W1, 50, "ok")           # valore globale da ingest API: legittimo
    resp = client.post(KPI_DEF_URL, {
        "kpi_code": "dr_test_age_days", "name": "DR", "source": "internal", "aggregation": "success_rate",
        "plant": str(pl.pk), "threshold_direction": "below",
    }, format="json")
    assert resp.status_code == 201, resp.data
    assert not _live(glob, pl).exists()
    assert _live(glob, tn).count() == 1
    assert _live(glob, None).count() == 1
    # soft delete, non DELETE: la riga resta recuperabile
    assert OperationalKpiSnapshot.objects.all_with_deleted().filter(kpi_definition=glob, plant=pl).exists()


def test_reader_never_shows_ghost_instead_of_real_value(pl, tn):
    glob = _def()
    site = _def(plant=pl)
    _snap(glob, pl, W2, None, "no_data")      # fantasma (ex globale), anche più recente
    _snap(site, pl, W1, 120, "ok")            # valore reale della definizione di sito
    _snap(glob, tn, W2, 30, "ok")

    view = get_operational_kpi_summary(pl.pk)
    assert view["count"] == 1
    assert view["items"][0]["value"] == 120

    org = get_operational_kpi_summary(None, all_plants=True)
    keys = [(i["kpi_code"], i["plant_code"]) for i in org["items"]]
    assert len(keys) == len(set(keys))
    by_plant = {i["plant_code"]: i for i in org["items"]}
    assert by_plant["KS-PL"]["value"] == 120
    assert by_plant["KS-TN"]["value"] == 30


# ── Disattivazione / cancellazione / riattivazione ───────────────────────────

def test_deactivate_prunes_and_reactivate_restores(client, pl):
    site = _def(plant=pl)
    _snap(site, pl, W1, 10, "ok")
    assert client.patch(f"{KPI_DEF_URL}{site.pk}/", {"is_active": False}, format="json").status_code == 200
    assert not _live(site).exists()
    assert client.patch(f"{KPI_DEF_URL}{site.pk}/", {"is_active": True}, format="json").status_code == 200
    assert _live(site).count() == 1


def test_delete_definition_prunes(client, pl):
    site = _def(plant=pl)
    _snap(site, pl, W1, 10, "ok")
    assert client.delete(f"{KPI_DEF_URL}{site.pk}/").status_code == 204
    assert not OperationalKpiSnapshot.objects.filter(kpi_definition_id=site.pk).exists()


def test_change_plant_prunes_old_site(client, pl, tn):
    site = _def(plant=pl)
    _snap(site, pl, W1, 10, "ok")
    assert client.patch(f"{KPI_DEF_URL}{site.pk}/", {"plant": str(tn.pk)}, format="json").status_code == 200
    assert not _live(site, pl).exists()


# ── Task settimanale e migration ─────────────────────────────────────────────

def test_compute_task_prunes_orphans_and_revives_recomputed_week(pl, tn, user):
    from apps.tasks import services
    from apps.tasks.tasks import compute_operational_kpis

    glob = _def(code="kpi_x", source="api")
    site = _def(code="kpi_x", plant=pl, source="api")
    dead = _def(code="kpi_dead", plant=pl, active=False)
    _snap(glob, pl, W1, None, "no_data")          # fantasma
    _snap(glob, tn, W1, 5, "ok")                  # legittimo
    _snap(site, pl, W1, 7, "ok")                  # legittimo
    _snap(dead, pl, W1, 1, "ok")                  # definizione disattivata
    compute_operational_kpis.apply()
    assert not _live(glob, pl).exists()
    assert _live(glob, tn).exists() and _live(site, pl).exists()
    assert not _live(dead).exists()

    # Una misura nuova sulla stessa settimana di una riga tolta la ripristina
    # invece di violare il vincolo di unicità.
    dead.is_active = True
    dead.save()
    OperationalKpiSnapshot.objects.filter(kpi_definition=site).update(deleted_at=datetime.datetime(2026, 9, 1, tzinfo=datetime.timezone.utc))
    snap = services.record_manual_kpi_value(site, pl, 9, week_start=W1, user=user)
    assert snap.deleted_at is None and snap.value == 9
    assert OperationalKpiSnapshot.objects.all_with_deleted().filter(kpi_definition=site, plant=pl, week_start=W1).count() == 1


def test_data_migration_cleans_existing_orphans(pl, tn):
    from django.apps import apps as django_apps

    glob = _def()
    _def(plant=pl)
    _snap(glob, pl, W1, None, "no_data")
    _snap(glob, tn, W1, 3, "ok")
    migration = importlib.import_module("apps.tasks.migrations.0017_prune_out_of_scope_kpi_snapshots")
    migration.prune(django_apps, None)
    assert not _live(glob, pl).exists()
    assert _live(glob, tn).exists()
    # idempotente
    assert sync_snapshots_with_scope() == {"pruned": 0, "restored": 0, "by_definition": {}}


# ── Guardie ──────────────────────────────────────────────────────────────────

def test_manual_value_on_global_for_overridden_site_rejected(client, pl, tn):
    glob = _def(code="manual_kpi", source="api")
    _def(code="manual_kpi", plant=pl, source="api")
    url = f"{KPI_DEF_URL}{glob.pk}/record-value/"
    assert client.post(url, {"value": 3, "plant": str(pl.pk)}, format="json").status_code == 400
    assert client.post(url, {"value": 3, "plant": str(tn.pk)}, format="json").status_code == 201


def test_trend_one_point_per_week_from_definition_in_scope(client, pl):
    glob = _def()
    site = _def(plant=pl)
    OperationalKpiSnapshot.objects.bulk_create([
        OperationalKpiSnapshot(kpi_definition=glob, plant=pl, week_start=W1, value=None, status="no_data"),
    ])
    _snap(site, pl, W1, 120, "ok")
    resp = client.get(f"/api/v1/tasks/kpi-snapshots/trend/?kpi_code=dr_test_age_days&plant={pl.pk}")
    assert resp.status_code == 200
    assert [r["value"] for r in resp.data["results"]] == [120]

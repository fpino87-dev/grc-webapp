"""
Manutenzione periodica di apparati e impianti (M04).

L'asset tiene lo stato (cadenza, ultima, prossima, esito); il giro notturno
apre il promemoria; lo scadenzario mostra la scadenza.
"""
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

User = get_user_model()

FACILITY_URL = "/api/v1/assets/facility/"


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="maint@test.com", email="maint@test.com", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        username="sysmaint@test.com", email="sysmaint@test.com", password="x"
    )


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="MNT-P", name="Plant Manutenzione", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def ups(db, plant, user):
    from apps.assets.models import AssetFacility
    return AssetFacility.objects.create(
        plant=plant, name="UPS sala server", asset_type="FAC", category="ups",
        criticality=5, owner=user, maintenance_frequency_months=6,
        rated_autonomy_minutes=30,
    )


# ── Cadenza e scadenza ───────────────────────────────────────────────────────

@pytest.mark.django_db
def test_cadence_on_the_asset_wins_over_the_policy(ups):
    from apps.assets.services import resolve_maintenance_due_date

    base = datetime.date(2026, 3, 10)
    assert resolve_maintenance_due_date(ups, base=base) == datetime.date(2026, 9, 10)


@pytest.mark.django_db
def test_policy_cadence_applies_without_an_override(plant, user):
    """Senza cadenza sull'asset vale la policy del sito: 1 anno di default."""
    from apps.assets.models import AssetFacility
    from apps.assets.services import resolve_maintenance_due_date

    asset = AssetFacility.objects.create(
        plant=plant, name="Antincendio", asset_type="FAC", category="antincendio",
    )
    base = datetime.date(2026, 3, 10)
    assert resolve_maintenance_due_date(asset, base=base) == datetime.date(2027, 3, 10)


@pytest.mark.django_db
def test_semiannual_cadence_from_month_end_stays_in_the_calendar(ups):
    from apps.assets.services import resolve_maintenance_due_date

    assert resolve_maintenance_due_date(
        ups, base=datetime.date(2026, 8, 31)
    ) == datetime.date(2027, 2, 28)


@pytest.mark.django_db
def test_removing_the_cadence_takes_the_asset_out_of_the_schedule(ups):
    """Togliere la cadenza deve azzerare la scadenza, non lasciare l'asset
    appeso a una data vecchia nello scadenzario."""
    from apps.assets.services import apply_maintenance_schedule

    apply_maintenance_schedule(ups)
    assert ups.next_maintenance_date is not None

    ups.maintenance_frequency_months = None
    assert apply_maintenance_schedule(ups) is None
    ups.refresh_from_db()
    assert ups.next_maintenance_date is None


# ── Registrazione ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_recording_maintenance_moves_the_next_one_forward(ups, user):
    from apps.assets.services import record_maintenance

    record_maintenance(ups, user, date=datetime.date(2026, 5, 4), result="con_riserve")
    ups.refresh_from_db()
    assert ups.last_maintenance_date == datetime.date(2026, 5, 4)
    assert ups.last_maintenance_result == "con_riserve"
    assert ups.next_maintenance_date == datetime.date(2026, 11, 4)


@pytest.mark.django_db
def test_recording_maintenance_writes_audit_log(ups, user):
    from apps.assets.services import record_maintenance
    from core.audit import AuditLog

    record_maintenance(ups, user)
    assert AuditLog.objects.filter(
        action_code="asset.maintenance_recorded", entity_id=ups.id
    ).exists()


# ── Giro notturno ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_nightly_opens_a_task_for_overdue_maintenance(ups, superuser):
    from apps.assets.tasks import check_maintenance_due
    from apps.tasks.models import Task

    ups.next_maintenance_date = timezone.localdate() - datetime.timedelta(days=5)
    ups.save()

    check_maintenance_due()
    task = Task.objects.get(source_id=ups.pk)
    assert "SCADUTA" in task.title
    assert task.priority == "alta"
    assert task.assigned_to == ups.owner


@pytest.mark.django_db
def test_nightly_warns_inside_the_policy_notice_window(ups, superuser):
    from apps.assets.tasks import check_maintenance_due
    from apps.tasks.models import Task

    ups.next_maintenance_date = timezone.localdate() + datetime.timedelta(days=20)
    ups.save()

    check_maintenance_due()
    assert "20gg" in Task.objects.get(source_id=ups.pk).title


@pytest.mark.django_db
def test_nightly_ignores_deadlines_far_away(ups, superuser):
    from apps.assets.tasks import check_maintenance_due
    from apps.tasks.models import Task

    ups.next_maintenance_date = timezone.localdate() + datetime.timedelta(days=120)
    ups.save()

    check_maintenance_due()
    assert not Task.objects.filter(source_id=ups.pk).exists()


@pytest.mark.django_db
def test_nightly_does_not_duplicate_the_reminder(ups, superuser):
    from apps.assets.tasks import check_maintenance_due
    from apps.tasks.models import Task

    ups.next_maintenance_date = timezone.localdate() - datetime.timedelta(days=2)
    ups.save()

    check_maintenance_due()
    check_maintenance_due()
    assert Task.objects.filter(source_id=ups.pk).count() == 1


@pytest.mark.django_db
def test_recorded_maintenance_reopens_the_alert_for_the_next_cycle(ups, superuser, user):
    """Segnalata la scadenza e registrata la manutenzione, alla scadenza
    successiva l'asset deve tornare a essere segnalato."""
    from apps.assets.services import record_maintenance
    from apps.assets.tasks import check_maintenance_due
    from apps.tasks.models import Task

    ups.next_maintenance_date = timezone.localdate() - datetime.timedelta(days=2)
    ups.save()
    check_maintenance_due()

    record_maintenance(ups, user)
    ups.refresh_from_db()
    ups.next_maintenance_date = timezone.localdate() - datetime.timedelta(days=1)
    ups.save()

    check_maintenance_due()
    assert Task.objects.filter(source_id=ups.pk).count() == 2


@pytest.mark.django_db
def test_nightly_schedules_assets_that_have_a_cadence_but_no_date(plant, superuser):
    from apps.assets.models import AssetFacility
    from apps.assets.tasks import check_maintenance_due

    asset = AssetFacility.objects.create(
        plant=plant, name="Gruppo elettrogeno", asset_type="FAC",
        category="gruppo_elettrogeno", maintenance_frequency_months=12,
    )
    check_maintenance_due()
    asset.refresh_from_db()
    assert asset.next_maintenance_date == timezone.localdate() + datetime.timedelta(days=365)


@pytest.mark.django_db
def test_assets_without_a_cadence_are_left_alone(plant, superuser):
    from apps.assets.models import AssetFacility
    from apps.assets.tasks import check_maintenance_due
    from apps.tasks.models import Task

    asset = AssetFacility.objects.create(
        plant=plant, name="Telecamera ingresso", asset_type="FAC",
        category="videosorveglianza",
    )
    check_maintenance_due()
    asset.refresh_from_db()
    assert asset.next_maintenance_date is None
    assert not Task.objects.filter(source_id=asset.pk).exists()


# ── Scadenzario ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_maintenance_appears_in_the_activity_schedule(ups, plant):
    from apps.compliance_schedule.services import get_activity_schedule

    ups.next_maintenance_date = timezone.localdate() + datetime.timedelta(days=15)
    ups.save()

    activities = get_activity_schedule(plant=plant)
    assert "Manutenzione: UPS sala server" in [a["label"] for a in activities]


# ── API ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_facility_via_api_schedules_maintenance(client, plant):
    resp = client.post(FACILITY_URL, {
        "plant": str(plant.id),
        "name": "UPS quadro generale",
        "category": "ups",
        "criticality": 5,
        "maintenance_frequency_months": 6,
        "rated_autonomy_minutes": 45,
    }, format="json")
    assert resp.status_code == 201, resp.data
    assert resp.data["next_maintenance_date"] is not None
    assert resp.data["asset_type"] == "FAC"
    assert resp.data["category_display"] == "UPS / gruppo di continuità"


@pytest.mark.django_db
def test_changing_the_cadence_recomputes_the_due_date(client, ups):
    from apps.assets.services import apply_maintenance_schedule

    apply_maintenance_schedule(ups)
    before = ups.next_maintenance_date

    resp = client.patch(f"{FACILITY_URL}{ups.id}/",
                        {"maintenance_frequency_months": 3}, format="json")
    assert resp.status_code == 200, resp.data
    ups.refresh_from_db()
    assert ups.next_maintenance_date < before


@pytest.mark.django_db
def test_rated_autonomy_is_rejected_on_facilities_without_a_battery(client, plant):
    resp = client.post(FACILITY_URL, {
        "plant": str(plant.id),
        "name": "Rilevatore fumi reparto",
        "category": "antincendio",
        "rated_autonomy_minutes": 30,
    }, format="json")
    assert resp.status_code == 400
    assert "rated_autonomy_minutes" in resp.data


@pytest.mark.django_db
def test_record_maintenance_action(client, ups):
    resp = client.post(f"{FACILITY_URL}{ups.id}/record-maintenance/",
                       {"result": "superata", "notes": "Prova autonomia 28 min"},
                       format="json")
    assert resp.status_code == 200, resp.data
    assert resp.data["last_maintenance_date"] == str(timezone.localdate())
    assert resp.data["maintenance_is_overdue"] is False


@pytest.mark.django_db
def test_record_maintenance_requires_a_cadence(client, plant):
    from apps.assets.models import AssetFacility
    asset = AssetFacility.objects.create(
        plant=plant, name="Varco badge", asset_type="FAC", category="controllo_accessi",
    )
    resp = client.post(f"{FACILITY_URL}{asset.id}/record-maintenance/", {}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_maintenance_due_list_endpoint(client, ups):
    ups.next_maintenance_date = timezone.localdate() - datetime.timedelta(days=1)
    ups.save()
    resp = client.get(f"{FACILITY_URL}maintenance-due/")
    assert resp.status_code == 200
    assert [a["name"] for a in resp.data] == ["UPS sala server"]


@pytest.mark.django_db
def test_maintenance_fields_are_exposed_on_it_assets_too(client, plant):
    """I quattro campi stanno sulla classe base: valgono per IT, OT e SW."""
    from apps.assets.models import AssetIT
    asset = AssetIT.objects.create(
        plant=plant, name="Server ERP", asset_type="IT", maintenance_frequency_months=12,
    )
    resp = client.get(f"/api/v1/assets/it/{asset.id}/")
    assert resp.status_code == 200
    assert resp.data["maintenance_frequency_months"] == 12
    assert "maintenance_is_overdue" in resp.data


# ── KPI ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_maintenance_kpis_read_the_registry(ups, plant):
    from apps.tasks.kpi_connectors import (
        facility_check_age_days, maintenance_overdue_count,
        maintenance_plan_compliance_rate,
    )
    from apps.tasks.services import _monday_of

    ups.next_maintenance_date = timezone.localdate() - datetime.timedelta(days=3)
    ups.last_maintenance_date = timezone.localdate() - datetime.timedelta(days=200)
    ups.save()
    week = _monday_of(timezone.localdate())

    assert maintenance_plan_compliance_rate(plant, week)["value"] == 0.0
    assert maintenance_overdue_count(plant, week)["value"] == 1.0
    assert facility_check_age_days(plant, week)["value"] == 200.0


@pytest.mark.django_db
def test_facility_never_checked_counts_from_installation(plant):
    from apps.assets.models import AssetFacility
    from apps.tasks.kpi_connectors import facility_check_age_days
    from apps.tasks.services import _monday_of

    AssetFacility.objects.create(
        plant=plant, name="Antincendio", asset_type="FAC", category="antincendio",
        installation_date=timezone.localdate() - datetime.timedelta(days=500),
    )
    res = facility_check_age_days(plant, _monday_of(timezone.localdate()))
    assert res["value"] == 500.0
    assert "mai verificati" in res["note"]

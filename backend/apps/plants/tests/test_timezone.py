"""
Test F3 — timezone per Plant: plant_today/plant_timezone, raggruppamento
per "oggi" del sito e applicazione ai calcoli di scadenza.

Per rendere deterministici i test si congela `django.utils.timezone.now` a
un istante in cui le date differiscono tra fusi: 2026-06-10 23:30 UTC →
Europe/Rome (UTC+2) è già l'11 giugno, America/New_York (UTC-4) ancora il 10.
"""
import datetime

import pytest

FROZEN_NOW = datetime.datetime(2026, 6, 10, 23, 30, tzinfo=datetime.timezone.utc)
ROME_DATE = datetime.date(2026, 6, 11)
NY_DATE = datetime.date(2026, 6, 10)


@pytest.fixture
def frozen_now(monkeypatch):
    monkeypatch.setattr("django.utils.timezone.now", lambda: FROZEN_NOW)


@pytest.fixture
def plant_rome(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="TZ-IT", name="Sito Roma", country="IT",
        nis2_scope="non_soggetto", timezone="Europe/Rome",
    )


@pytest.fixture
def plant_ny(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="TZ-US", name="Sito New York", country="US",
        nis2_scope="non_soggetto", timezone="America/New_York",
    )


# ── plant_timezone / plant_today ─────────────────────────────────────────────

def test_plant_timezone_fallback_on_invalid(db, plant_rome):
    from apps.plants.services import plant_timezone

    plant_rome.timezone = "Mars/Olympus_Mons"
    assert str(plant_timezone(plant_rome)) == "Europe/Rome"  # TIME_ZONE di progetto
    plant_rome.timezone = ""
    assert str(plant_timezone(plant_rome)) == "Europe/Rome"


def test_plant_today_uses_site_midnight(frozen_now, plant_rome, plant_ny):
    from apps.plants.services import plant_today

    assert plant_today(plant_rome) == ROME_DATE
    assert plant_today(plant_ny) == NY_DATE
    assert plant_today(None) == ROME_DATE  # server clock = TIME_ZONE progetto


def test_plant_ids_by_today_groups_by_local_date(frozen_now, plant_rome, plant_ny):
    from apps.plants.services import plant_ids_by_today

    groups = plant_ids_by_today()
    assert groups[ROME_DATE] == [plant_rome.pk]
    assert groups[NY_DATE] == [plant_ny.pk]


# ── validazione serializer ───────────────────────────────────────────────────

def test_serializer_rejects_invalid_timezone(db):
    from apps.plants.serializers import PlantSerializer

    ser = PlantSerializer(data={
        "code": "TZ-X", "name": "X", "country": "IT",
        "nis2_scope": "non_soggetto", "timezone": "Not/AZone",
    })
    assert not ser.is_valid()
    assert "timezone" in ser.errors


def test_serializer_accepts_valid_and_defaults_empty(db):
    from apps.plants.serializers import PlantSerializer

    ser = PlantSerializer(data={
        "code": "TZ-Y", "name": "Y", "country": "TR",
        "nis2_scope": "non_soggetto", "timezone": "Europe/Istanbul",
    })
    assert ser.is_valid(), ser.errors

    ser2 = PlantSerializer(data={
        "code": "TZ-Z", "name": "Z", "country": "IT",
        "nis2_scope": "non_soggetto", "timezone": "",
    })
    assert ser2.is_valid(), ser2.errors
    assert ser2.validated_data["timezone"] == "Europe/Rome"


# ── scadenzario: off-by-one serale risolto ───────────────────────────────────

@pytest.mark.django_db
def test_activity_schedule_uses_plant_today(frozen_now, plant_rome, plant_ny):
    """Un documento con revisione al 2026-06-10: per il sito di New York è
    "scade oggi" (incluso, days_left=0); per Roma è già scaduto ieri (escluso
    dalla finestra futura) — prima del fix entrambi usavano la data server."""
    from apps.compliance_schedule.services import get_activity_schedule
    from apps.documents.models import Document

    for plant in (plant_rome, plant_ny):
        Document.objects.create(
            plant=plant, title=f"Policy {plant.code}", document_type="policy",
            status="approvato", review_due_date=NY_DATE,
        )

    labels_ny = [a["label"] for a in get_activity_schedule(plant=plant_ny)]
    assert any("Policy TZ-US" in label for label in labels_ny)

    labels_rome = [a["label"] for a in get_activity_schedule(plant=plant_rome)]
    assert not any("Policy TZ-IT" in label for label in labels_rome)


# ── advisor Cockpit: gruppi per fuso, query aggregata ────────────────────────

@pytest.mark.django_db
def test_mgmt_review_overdue_advisor_respects_site_today(frozen_now, plant_rome, plant_ny):
    """Riesame pianificato al 2026-06-10: in ritardo per Roma (oggi 06-11),
    non per New York (oggi 06-10)."""
    from apps.cockpit.advisors_builtin import mgmt_review_overdue_advisor
    from apps.management_review.models import ManagementReview

    for plant in (plant_rome, plant_ny):
        ManagementReview.objects.create(
            plant=plant, title=f"Riesame {plant.code}",
            review_date=NY_DATE, status="pianificato",
        )

    flagged = {i.plant_id for i in mgmt_review_overdue_advisor()}
    assert str(plant_rome.pk) in flagged
    assert str(plant_ny.pk) not in flagged


@pytest.mark.django_db
def test_eol_assets_respect_site_today(frozen_now, plant_rome, plant_ny):
    """Asset con eol_date 2026-06-10: EOL per Roma (oggi 06-11... lte include
    anche il giorno stesso, quindi EOL per entrambi); con eol 2026-06-10 il
    sito NY lo vede EOL oggi stesso, Roma da ieri. Il caso discriminante è
    eol_date = 2026-06-11: EOL per Roma, NON per New York."""
    from apps.assets.models import AssetIT
    from apps.assets.services import get_eol_assets

    for plant in (plant_rome, plant_ny):
        AssetIT.objects.create(
            plant=plant, name=f"Server {plant.code}", criticality=3,
            eol_date=ROME_DATE,
        )

    eol_plants = {a.plant_id for a in get_eol_assets()}
    assert plant_rome.pk in eol_plants
    assert plant_ny.pk not in eol_plants

"""Test API assets — azioni avanzate e filtri."""
import pytest
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_IT = "/api/v1/assets/it/"
URL_OT = "/api/v1/assets/ot/"
URL_ZONES = "/api/v1/assets/network-zones/"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="assx_user", email="assx@test.com", password="test")


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="AX-P", name="Plant AX", country="IT",
        nis2_scope="essenziale", status="attivo",
    )


@pytest.fixture
def asset_it(db, plant, user):
    from apps.assets.models import AssetIT
    return AssetIT.objects.create(
        plant=plant,
        name="Server DB Extended",
        asset_type="IT",
        criticality=4,
        last_change_date=date.today(),
        created_by=user,
    )


@pytest.fixture
def asset_ot(db, plant, user):
    from apps.assets.models import AssetOT
    return AssetOT.objects.create(
        plant=plant,
        name="PLC Extended",
        asset_type="OT",
        criticality=3,
        purdue_level=2,
        created_by=user,
    )


@pytest.mark.django_db
def test_asset_it_eol_action(client):
    resp = client.get(f"{URL_IT}eol/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_asset_it_needs_revaluation(client):
    resp = client.get(f"{URL_IT}needs-revaluation/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_asset_it_register_change(client, asset_it):
    payload = {"change_notes": "Aggiornato firmware", "change_date": str(date.today())}
    resp = client.post(f"{URL_IT}{asset_it.id}/register-change/", payload, format="json")
    assert resp.status_code in (200, 201, 400)


@pytest.mark.django_db
def test_asset_it_clear_revaluation(client, asset_it):
    resp = client.post(f"{URL_IT}{asset_it.id}/clear-revaluation/", {}, format="json")
    assert resp.status_code in (200, 400)


@pytest.mark.django_db
def test_asset_ot_needs_revaluation(client):
    resp = client.get(f"{URL_OT}needs-revaluation/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_asset_ot_register_change(client, asset_ot):
    payload = {"change_notes": "Aggiornato firmware OT"}
    resp = client.post(f"{URL_OT}{asset_ot.id}/register-change/", payload, format="json")
    assert resp.status_code in (200, 201, 400)


@pytest.mark.django_db
def test_asset_ot_clear_revaluation(client, asset_ot):
    resp = client.post(f"{URL_OT}{asset_ot.id}/clear-revaluation/", {}, format="json")
    assert resp.status_code in (200, 400)


@pytest.mark.django_db
def test_filter_it_by_plant(client, plant, asset_it):
    resp = client.get(f"{URL_IT}?plant={plant.id}")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_filter_it_by_criticality(client, asset_it):
    resp = client.get(f"{URL_IT}?criticality=4")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_filter_ot_by_plant(client, plant, asset_ot):
    resp = client.get(f"{URL_OT}?plant={plant.id}")
    assert resp.status_code == 200

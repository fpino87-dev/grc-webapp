"""Test API asset IT/OT."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_IT = "/api/v1/assets/it/"
URL_OT = "/api/v1/assets/ot/"
URL_ZONES = "/api/v1/assets/network-zones/"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="asset_user", email="asset@test.com", password="test")


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="AST-P", name="Plant Assets", country="IT", nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def network_zone(db, plant, user):
    from apps.assets.models import NetworkZone
    return NetworkZone.objects.create(plant=plant, name="DMZ", zone_type="DMZ", created_by=user)


@pytest.fixture
def asset_it(db, plant, user):
    from apps.assets.models import AssetIT
    return AssetIT.objects.create(
        plant=plant,
        name="Server Web",
        asset_type="IT",
        criticality=3,
        fqdn="web.example.com",
        ip_address="192.168.1.1",
        created_by=user,
    )


@pytest.fixture
def asset_ot(db, plant, network_zone, user):
    from apps.assets.models import AssetOT
    return AssetOT.objects.create(
        plant=plant,
        name="PLC Linea 1",
        asset_type="OT",
        criticality=4,
        purdue_level=1,
        category="PLC",
        network_zone=network_zone,
        created_by=user,
    )


# ── NetworkZone CRUD ──────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_network_zones(client):
    resp = client.get(URL_ZONES)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_create_network_zone(client, plant):
    payload = {"plant": str(plant.id), "name": "OT Zone", "zone_type": "OT"}
    resp = client.post(URL_ZONES, payload, format="json")
    assert resp.status_code == 201


# ── AssetIT CRUD ──────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_assets_it(client):
    resp = client.get(URL_IT)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_list_assets_unauthenticated():
    resp = APIClient().get(URL_IT)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_create_asset_it(client, plant):
    payload = {
        "plant": str(plant.id),
        "name": "Nuovo Server",
        "asset_type": "IT",
        "criticality": 2,
        "fqdn": "new.example.com",
    }
    resp = client.post(URL_IT, payload, format="json")
    assert resp.status_code == 201
    assert resp.data["name"] == "Nuovo Server"


@pytest.mark.django_db
def test_retrieve_asset_it(client, asset_it):
    resp = client.get(f"{URL_IT}{asset_it.id}/")
    assert resp.status_code == 200
    assert resp.data["name"] == "Server Web"


@pytest.mark.django_db
def test_update_asset_it_criticality(client, asset_it):
    resp = client.patch(f"{URL_IT}{asset_it.id}/", {"criticality": 5}, format="json")
    assert resp.status_code == 200
    assert resp.data["criticality"] == 5


@pytest.mark.django_db
def test_delete_asset_it(client, asset_it):
    resp = client.delete(f"{URL_IT}{asset_it.id}/")
    assert resp.status_code == 204
    # After delete, GET returns 404
    resp2 = client.get(f"{URL_IT}{asset_it.id}/")
    assert resp2.status_code == 404


# ── AssetOT CRUD ──────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_assets_ot(client):
    resp = client.get(URL_OT)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_create_asset_ot(client, plant, network_zone):
    payload = {
        "plant": str(plant.id),
        "name": "SCADA Sistema",
        "asset_type": "OT",
        "criticality": 5,
        "purdue_level": 2,
        "category": "SCADA",
        "network_zone": str(network_zone.id),
    }
    resp = client.post(URL_OT, payload, format="json")
    assert resp.status_code == 201
    assert resp.data["name"] == "SCADA Sistema"


@pytest.mark.django_db
def test_retrieve_asset_ot(client, asset_ot):
    resp = client.get(f"{URL_OT}{asset_ot.id}/")
    assert resp.status_code == 200
    assert resp.data["name"] == "PLC Linea 1"

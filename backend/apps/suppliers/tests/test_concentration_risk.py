"""P2-4 — catena concentrazione fornitura → risk.

Verifica `get_concentration_risk_register`: il campo finora inerte
`Supplier.supply_concentration_pct` diventa un registro rischi (soglia TPRM →
livello di rischio, con bump NIS2), esposto via API plant-scoped.
"""
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.plants.models import Plant
from apps.suppliers.models import Supplier
from apps.suppliers.services import get_concentration_risk_register

User = get_user_model()
pytestmark = pytest.mark.django_db

URL = "/api/v1/suppliers/suppliers/concentration-risks/"


def _sup(name, pct, nis2=False, status="attivo", plants=None):
    s = Supplier.objects.create(
        name=name,
        supply_concentration_pct=(None if pct is None else Decimal(str(pct))),
        nis2_relevant=nis2, status=status,
    )
    if plants:
        s.plants.set(plants)
    return s


@pytest.fixture
def plant(db):
    return Plant.objects.create(
        code="CR-P", name="Plant CR", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


# ── service ─────────────────────────────────────────────────────────────────


def test_media_maps_to_medio():
    _sup("Media Srl", 35)
    reg = get_concentration_risk_register()
    assert reg["count"] == 1
    assert reg["items"][0]["threshold"] == "media"
    assert reg["items"][0]["risk_level"] == "medio"


def test_critica_maps_to_alto():
    _sup("Critica Srl", 70)
    reg = get_concentration_risk_register()
    assert reg["items"][0]["threshold"] == "critica"
    assert reg["items"][0]["risk_level"] == "alto"


def test_nis2_bump_critica_to_critico():
    _sup("Critica NIS2", 80, nis2=True)
    reg = get_concentration_risk_register()
    assert reg["items"][0]["risk_level"] == "critico"


def test_nis2_bump_media_to_alto():
    _sup("Media NIS2", 30, nis2=True)
    reg = get_concentration_risk_register()
    assert reg["items"][0]["risk_level"] == "alto"


def test_bassa_excluded():
    _sup("Bassa Srl", 10)
    assert get_concentration_risk_register()["count"] == 0


def test_null_concentration_excluded():
    _sup("Senza dato", None)
    assert get_concentration_risk_register()["count"] == 0


def test_inactive_supplier_excluded():
    _sup("Dismesso", 90, status="terminato")
    assert get_concentration_risk_register()["count"] == 0


def test_boundary_20_is_media():
    # concentration_threshold: <20 bassa, <=50 media → 20 è media
    _sup("Confine 20", 20)
    reg = get_concentration_risk_register()
    assert reg["count"] == 1
    assert reg["items"][0]["threshold"] == "media"


def test_counts_and_attention():
    _sup("A", 35)                 # medio
    _sup("B", 70)                 # alto
    _sup("C", 80, nis2=True)      # critico
    reg = get_concentration_risk_register()
    assert reg["by_level"] == {"medio": 1, "alto": 1, "critico": 1}
    assert reg["attention"] == 2   # alto + critico


def test_sorted_by_severity_then_pct():
    _sup("Medio", 30)
    _sup("Critico", 90, nis2=True)
    _sup("Alto", 60)
    levels = [i["risk_level"] for i in get_concentration_risk_register()["items"]]
    assert levels == ["critico", "alto", "medio"]


def test_item_includes_plants(plant):
    _sup("Con plant", 70, plants=[plant])
    item = get_concentration_risk_register()["items"][0]
    assert item["plants"] == ["Plant CR"]


# ── API ─────────────────────────────────────────────────────────────────────


def test_api_concentration_risks_org_scope(db):
    u = User.objects.create_user(username="cr", email="cr@t.com", password="x")
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    _sup("Critica Srl", 70)
    _sup("Bassa Srl", 5)

    client = APIClient()
    client.force_authenticate(user=u)
    resp = client.get(URL)
    assert resp.status_code == 200
    assert resp.data["count"] == 1
    assert resp.data["items"][0]["supplier_name"] == "Critica Srl"


def test_api_concentration_risks_plant_scoped(db):
    """Un utente con scope su un solo plant non vede la concentrazione di
    fornitori legati esclusivamente ad altri plant."""
    from apps.auth_grc.models import GrcRole, UserPlantAccess

    p1 = Plant.objects.create(code="CR-1", name="P1", country="IT", nis2_scope="non_soggetto", status="attivo")
    p2 = Plant.objects.create(code="CR-2", name="P2", country="IT", nis2_scope="non_soggetto", status="attivo")
    _sup("Solo P2", 70, plants=[p2])

    u = User.objects.create_user(username="cr2", email="cr2@t.com", password="x")
    access = UserPlantAccess.objects.create(user=u, role=GrcRole.RISK_MANAGER, scope_type="plant")
    access.scope_plants.set([p1])

    client = APIClient()
    client.force_authenticate(user=u)
    resp = client.get(URL)
    assert resp.status_code == 200
    names = [i["supplier_name"] for i in resp.data["items"]]
    assert "Solo P2" not in names

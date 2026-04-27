"""
Test deduplication L2/L3: quando un plant ha TISAX_L3, i controlli L2 che
hanno un corrispondente VH (relazione 'extends') non devono apparire nella lista.
"""
import pytest
from datetime import date
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()
URL_INSTANCES = "/api/v1/controls/instances/"


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="dedup_user", email="dedup@test.com", password="test")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def api_client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="DD-PLANT", name="Dedup Plant", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def l2l3_setup(db, plant):
    """
    Crea due framework TISAX_L2 / TISAX_L3 con un controllo base e uno VH
    collegati da 'extends', più un controllo L2-only senza corrispondente VH.
    """
    from apps.controls.models import Control, ControlInstance, ControlMapping, Framework
    from apps.plants.models import PlantFramework

    fw_l2 = Framework.objects.create(
        code="TISAX_L2_DD", name="TISAX L2 Dedup", version="6.0", published_at=date.today()
    )
    fw_l3 = Framework.objects.create(
        code="TISAX_L3_DD", name="TISAX L3 Dedup", version="6.0", published_at=date.today()
    )

    # Controllo L2 base (sarà sostituito da VH)
    ctrl_l2_base = Control.objects.create(
        framework=fw_l2, external_id="ISA-1.6.2-TEST", translations={}, level="L2"
    )
    # Controllo L2-only (nessun VH corrispondente — deve restare visibile)
    ctrl_l2_only = Control.objects.create(
        framework=fw_l2, external_id="ISA-2.1.1-TEST", translations={}, level="L2"
    )
    # Controllo L3/VH che estende il base
    ctrl_l3_vh = Control.objects.create(
        framework=fw_l3, external_id="ISA-1.6.2-VH-TEST", translations={}, level="L3"
    )
    # Mapping extends: VH → base L2
    ControlMapping.objects.create(
        source_control=ctrl_l3_vh,
        target_control=ctrl_l2_base,
        relationship="extends",
    )

    # Assegna entrambi i framework al plant
    PlantFramework.objects.create(
        plant=plant, framework=fw_l2, active_from=date.today(), level="AL2", active=True
    )
    PlantFramework.objects.create(
        plant=plant, framework=fw_l3, active_from=date.today(), level="AL3", active=True
    )

    # Crea ControlInstance per tutti e tre i controlli
    inst_base = ControlInstance.objects.create(plant=plant, control=ctrl_l2_base)
    inst_only = ControlInstance.objects.create(plant=plant, control=ctrl_l2_only)
    inst_vh   = ControlInstance.objects.create(plant=plant, control=ctrl_l3_vh)

    return {
        "fw_l2": fw_l2, "fw_l3": fw_l3,
        "ctrl_l2_base": ctrl_l2_base, "ctrl_l2_only": ctrl_l2_only, "ctrl_l3_vh": ctrl_l3_vh,
        "inst_base": inst_base, "inst_only": inst_only, "inst_vh": inst_vh,
    }


@pytest.mark.django_db
def test_l2_superseded_hidden_when_l3_assigned(api_client, plant, l2l3_setup):
    """ISA-1.6.2-TEST (L2) deve essere nascosto perché ISA-1.6.2-VH-TEST (L3) lo estende."""
    resp = api_client.get(URL_INSTANCES, {"plant": plant.id})
    assert resp.status_code == 200
    external_ids = [r["control_external_id"] for r in resp.data["results"]]
    assert "ISA-1.6.2-TEST" not in external_ids      # base L2 nascosto
    assert "ISA-1.6.2-VH-TEST" in external_ids       # VH visibile
    assert "ISA-2.1.1-TEST" in external_ids           # L2-only ancora visibile


@pytest.mark.django_db
def test_l2_only_visible_without_l3(db, plant):
    """Senza TISAX_L3, tutti i controlli L2 sono visibili (nessuna dedup)."""
    from apps.controls.models import Control, ControlInstance, Framework
    from apps.plants.models import PlantFramework

    fw = Framework.objects.create(
        code="TISAX_L2_NO3", name="TISAX L2 Solo", version="6.0", published_at=date.today()
    )
    ctrl = Control.objects.create(
        framework=fw, external_id="ISA-1.6.2-SOLO", translations={}, level="L2"
    )
    PlantFramework.objects.create(
        plant=plant, framework=fw, active_from=date.today(), level="AL2", active=True
    )
    ControlInstance.objects.create(plant=plant, control=ctrl)

    from apps.auth_grc.models import GrcRole, UserPlantAccess
    user = User.objects.create_user(username="solo_user2", email="solo2@test.com", password="test")
    UserPlantAccess.objects.create(user=user, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    c = APIClient()
    c.force_authenticate(user=user)
    resp = c.get(URL_INSTANCES, {"plant": plant.id})
    assert resp.status_code == 200
    external_ids = [r["control_external_id"] for r in resp.data["results"]]
    assert "ISA-1.6.2-SOLO" in external_ids

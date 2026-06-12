"""
Test C9 — l'owner di un ControlInstance è scoped al plant.

Prima del fix la tendina owner caricava i RoleAssignment org-wide e la PATCH
accettava qualsiasi user: si poteva assegnare un controllo di un plant a chi non
vi ha accesso. Ora:
  - l'endpoint /instances/eligible-owners/?plant= elenca solo chi ha accesso al
    plant via UserPlantAccess (org / bu / plant-list);
  - il serializer convalida l'owner sulla PATCH (difesa in profondità).
"""
import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_INSTANCES = "/api/v1/controls/instances/"


@pytest.fixture
def org_user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="org_owner", email="org@test.com", password="test")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def client(org_user):
    c = APIClient()
    c.force_authenticate(user=org_user)
    return c


@pytest.fixture
def topology(db):
    """Due plant in BU distinte + tre utenti con scope diversi.

    Restituisce un dict con plant_a, plant_b, e gli utenti:
      - bu_a_user: scope bu == plant_a.bu  → accesso a plant_a, non a plant_b
      - plant_a_user: scope single_plant su plant_a
      - other_user: scope single_plant su plant_b  → nessun accesso a plant_a
    """
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    from apps.plants.models import BusinessUnit, Plant

    bu_a = BusinessUnit.objects.create(code="BU-A", name="BU A")
    bu_b = BusinessUnit.objects.create(code="BU-B", name="BU B")
    plant_a = Plant.objects.create(
        code="PA", name="Plant A", country="IT", bu=bu_a,
        nis2_scope="importante", status="attivo",
    )
    plant_b = Plant.objects.create(
        code="PB", name="Plant B", country="IT", bu=bu_b,
        nis2_scope="importante", status="attivo",
    )

    bu_a_user = User.objects.create_user(username="bu_a", email="bua@test.com", password="x")
    UserPlantAccess.objects.create(
        user=bu_a_user, role=GrcRole.PLANT_MANAGER, scope_type="bu", scope_bu=bu_a,
    )
    plant_a_user = User.objects.create_user(username="pa_user", email="pau@test.com", password="x")
    access_pa = UserPlantAccess.objects.create(
        user=plant_a_user, role=GrcRole.CONTROL_OWNER, scope_type="single_plant",
    )
    access_pa.scope_plants.add(plant_a)
    other_user = User.objects.create_user(username="pb_user", email="pbu@test.com", password="x")
    access_pb = UserPlantAccess.objects.create(
        user=other_user, role=GrcRole.CONTROL_OWNER, scope_type="single_plant",
    )
    access_pb.scope_plants.add(plant_b)

    return {
        "plant_a": plant_a, "plant_b": plant_b,
        "bu_a_user": bu_a_user, "plant_a_user": plant_a_user, "other_user": other_user,
    }


@pytest.fixture
def instance_a(db, org_user, topology):
    from apps.controls.models import Control, ControlInstance, Framework
    from apps.plants.models import PlantFramework

    plant = topology["plant_a"]
    fw = Framework.objects.create(
        code="ISO-OW", name="ISO OW", version="2022", published_at=timezone.localdate(),
    )
    PlantFramework.objects.create(
        plant=plant, framework=fw, active_from=timezone.localdate(), level="L2", active=True,
    )
    control = Control.objects.create(
        framework=fw, external_id="OW-1.1",
        translations={"it": {"title": "Controllo OW"}}, evidence_requirement={},
    )
    return ControlInstance.objects.create(
        plant=plant, control=control, status="non_valutato", created_by=org_user,
    )


# ---- service: eligible_owners_for_plant ----

@pytest.mark.django_db
def test_eligible_owners_includes_org_bu_and_plant_scope(topology, org_user):
    from apps.auth_grc.services import eligible_owners_for_plant

    ids = {o["id"] for o in eligible_owners_for_plant(topology["plant_a"])}
    assert org_user.id in ids            # scope org
    assert topology["bu_a_user"].id in ids   # scope bu == plant_a.bu
    assert topology["plant_a_user"].id in ids  # single_plant su plant_a
    assert topology["other_user"].id not in ids  # scoped solo su plant_b


@pytest.mark.django_db
def test_eligible_owners_excludes_inactive_and_deleted(topology):
    from apps.auth_grc.models import UserPlantAccess
    from apps.auth_grc.services import eligible_owners_for_plant

    topology["plant_a_user"].is_active = False
    topology["plant_a_user"].save(update_fields=["is_active"])
    # bu_a_user: revoca l'accesso (soft delete)
    UserPlantAccess.objects.filter(user=topology["bu_a_user"]).update(
        deleted_at=timezone.now()
    )

    ids = {o["id"] for o in eligible_owners_for_plant(topology["plant_a"])}
    assert topology["plant_a_user"].id not in ids
    assert topology["bu_a_user"].id not in ids


# ---- endpoint ----

@pytest.mark.django_db
def test_eligible_owners_endpoint_requires_plant(client):
    resp = client.get(f"{URL_INSTANCES}eligible-owners/")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_eligible_owners_endpoint_returns_scoped_users(client, topology):
    resp = client.get(f"{URL_INSTANCES}eligible-owners/", {"plant": str(topology["plant_a"].id)})
    assert resp.status_code == 200
    ids = {o["id"] for o in resp.json()}
    assert topology["plant_a_user"].id in ids
    assert topology["other_user"].id not in ids


# ---- serializer integrity on PATCH ----

@pytest.mark.django_db
def test_patch_owner_with_plant_access_ok(client, instance_a, topology):
    resp = client.patch(
        f"{URL_INSTANCES}{instance_a.id}/",
        {"owner": topology["plant_a_user"].id}, format="json",
    )
    assert resp.status_code == 200
    instance_a.refresh_from_db()
    assert instance_a.owner_id == topology["plant_a_user"].id


@pytest.mark.django_db
def test_patch_owner_without_plant_access_rejected(client, instance_a, topology):
    resp = client.patch(
        f"{URL_INSTANCES}{instance_a.id}/",
        {"owner": topology["other_user"].id}, format="json",
    )
    assert resp.status_code == 400
    instance_a.refresh_from_db()
    assert instance_a.owner_id is None


@pytest.mark.django_db
def test_patch_owner_null_clears_without_check(client, instance_a, topology):
    """Assegnare un owner valido e poi azzerarlo (owner=null) è sempre permesso."""
    instance_a.owner = topology["plant_a_user"]
    instance_a.save(update_fields=["owner"])
    resp = client.patch(
        f"{URL_INSTANCES}{instance_a.id}/", {"owner": None}, format="json",
    )
    assert resp.status_code == 200
    instance_a.refresh_from_db()
    assert instance_a.owner_id is None

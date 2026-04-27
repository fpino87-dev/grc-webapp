"""Test claims JWT (newfix R2): roles + roles_by_plant + role legacy.

Un utente con piu' UserPlantAccess deve esporre nel JWT TUTTI i ruoli, non
solo il primo trovato a caso. Il claim legacy `role` resta come "ruolo piu'
alto" per retro-compatibilita' UI.
"""
import pytest
from django.contrib.auth import get_user_model

from apps.auth_grc.models import GrcRole, UserPlantAccess
from apps.plants.models import Plant
from core.jwt import GrcTokenObtainPairSerializer, _highest_role

User = get_user_model()


@pytest.fixture
def plant_a(db):
    return Plant.objects.create(
        code="JWT-A", name="Plant A", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def plant_b(db):
    return Plant.objects.create(
        code="JWT-B", name="Plant B", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.mark.django_db
def test_jwt_user_without_access_has_role_user():
    user = User.objects.create_user(username="noaccjwt", email="noacc@test", password="x")
    token = GrcTokenObtainPairSerializer.get_token(user)
    assert token["role"] == "user"
    assert token["roles"] == []
    assert token["roles_by_plant"] == {}


@pytest.mark.django_db
def test_jwt_superuser_without_access_falls_back_to_super_admin():
    user = User.objects.create_user(
        username="sujwt", email="sujwt@test", password="x", is_superuser=True,
    )
    token = GrcTokenObtainPairSerializer.get_token(user)
    assert token["role"] == "super_admin"
    assert token["roles"] == ["super_admin"]


@pytest.mark.django_db
def test_jwt_multiple_accesses_returns_all_roles(plant_a, plant_b):
    """RM su Plant A + Internal Auditor su Plant B → entrambi nel claim."""
    user = User.objects.create_user(username="multi", email="multi@test", password="x")
    a1 = UserPlantAccess.objects.create(
        user=user, role=GrcRole.RISK_MANAGER, scope_type="single_plant",
    )
    a1.scope_plants.set([plant_a])
    a2 = UserPlantAccess.objects.create(
        user=user, role=GrcRole.INTERNAL_AUDITOR, scope_type="single_plant",
    )
    a2.scope_plants.set([plant_b])

    token = GrcTokenObtainPairSerializer.get_token(user)
    assert set(token["roles"]) == {"risk_manager", "internal_auditor"}
    # Internal auditor batte risk_manager nella gerarchia.
    assert token["role"] == "internal_auditor"
    assert token["roles_by_plant"] == {
        str(plant_a.pk): ["risk_manager"],
        str(plant_b.pk): ["internal_auditor"],
    }


@pytest.mark.django_db
def test_jwt_org_scope_uses_org_key():
    user = User.objects.create_user(username="org", email="org@test", password="x")
    UserPlantAccess.objects.create(
        user=user, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org",
    )
    token = GrcTokenObtainPairSerializer.get_token(user)
    assert token["roles"] == ["compliance_officer"]
    assert token["role"] == "compliance_officer"
    assert token["roles_by_plant"] == {"__org__": ["compliance_officer"]}


@pytest.mark.django_db
def test_jwt_soft_deleted_access_excluded(plant_a):
    user = User.objects.create_user(username="del", email="del@test", password="x")
    a = UserPlantAccess.objects.create(
        user=user, role=GrcRole.PLANT_MANAGER, scope_type="single_plant",
    )
    a.scope_plants.set([plant_a])
    a.soft_delete()
    token = GrcTokenObtainPairSerializer.get_token(user)
    assert token["roles"] == []
    assert token["role"] == "user"


def test_highest_role_picks_top_of_hierarchy():
    assert _highest_role({"plant_manager", "compliance_officer"}) == "compliance_officer"
    assert _highest_role({"risk_manager", "control_owner"}) == "risk_manager"
    assert _highest_role({"unknown_role"}) == "unknown_role"
    assert _highest_role(set()) == "user"

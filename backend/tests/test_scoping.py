"""Test del mixin RBAC plant scoping (core/scoping.py)."""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from core.scoping import get_user_plant_ids, scope_queryset_by_plant

User = get_user_model()


def _grant(user, role, *, scope_type, plants=None, bu=None):
    from apps.auth_grc.models import UserPlantAccess
    access = UserPlantAccess.objects.create(
        user=user, role=role, scope_type=scope_type, scope_bu=bu,
    )
    if plants:
        access.scope_plants.set(plants)
    return access


@pytest.fixture
def plant_a(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="SC-A", name="Plant A", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def plant_b(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="SC-B", name="Plant B", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def pm_a(db, plant_a):
    from apps.auth_grc.models import GrcRole
    user = User.objects.create_user(
        username="pm_a", email="pm_a@test.com", password="test",
    )
    _grant(user, GrcRole.PLANT_MANAGER, scope_type="single_plant", plants=[plant_a])
    return user


@pytest.fixture
def pm_b(db, plant_b):
    from apps.auth_grc.models import GrcRole
    user = User.objects.create_user(
        username="pm_b", email="pm_b@test.com", password="test",
    )
    _grant(user, GrcRole.PLANT_MANAGER, scope_type="single_plant", plants=[plant_b])
    return user


@pytest.fixture
def org_user(db):
    from apps.auth_grc.models import GrcRole
    user = User.objects.create_user(
        username="org", email="org@test.com", password="test",
    )
    _grant(user, GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return user


@pytest.fixture
def no_access_user(db):
    return User.objects.create_user(
        username="noacc", email="noacc@test.com", password="test",
    )


@pytest.fixture
def superuser(db):
    return User.objects.create_user(
        username="su", email="su@test.com", password="test", is_superuser=True,
    )


# ── get_user_plant_ids ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_org_scope_returns_none(org_user):
    assert get_user_plant_ids(org_user) is None


@pytest.mark.django_db
def test_superuser_returns_none(superuser):
    assert get_user_plant_ids(superuser) is None


@pytest.mark.django_db
def test_no_access_returns_empty_set(no_access_user):
    assert get_user_plant_ids(no_access_user) == set()


@pytest.mark.django_db
def test_unauthenticated_returns_empty_set():
    from django.contrib.auth.models import AnonymousUser
    assert get_user_plant_ids(AnonymousUser()) == set()


@pytest.mark.django_db
def test_single_plant_access(pm_a, plant_a, plant_b):
    ids = get_user_plant_ids(pm_a)
    assert ids == {plant_a.id}
    assert plant_b.id not in ids


@pytest.mark.django_db
def test_bu_scope_includes_all_plants_in_bu(db, plant_a, plant_b):
    from apps.auth_grc.models import GrcRole
    from apps.plants.models import BusinessUnit
    bu = BusinessUnit.objects.create(name="BU1", code="BU1")
    plant_a.bu = bu
    plant_a.save()
    plant_b.bu = bu
    plant_b.save()
    user = User.objects.create_user(username="bu_user", email="bu@test.com", password="test")
    _grant(user, GrcRole.PLANT_MANAGER, scope_type="bu", bu=bu)
    ids = get_user_plant_ids(user)
    assert ids == {plant_a.id, plant_b.id}


# ── scope_queryset_by_plant ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_pm_a_does_not_see_plant_b_data(pm_a, plant_a, plant_b):
    """Caso d'uso S1: PM A non vede dati di Plant B."""
    from apps.tasks.models import Task
    Task.objects.create(plant=plant_a, title="A1", status="aperto", priority="media")
    Task.objects.create(plant=plant_b, title="B1", status="aperto", priority="media")
    qs = scope_queryset_by_plant(Task.objects.all(), pm_a)
    titles = set(qs.values_list("title", flat=True))
    assert titles == {"A1"}


@pytest.mark.django_db
def test_org_user_sees_all(org_user, plant_a, plant_b):
    from apps.tasks.models import Task
    Task.objects.create(plant=plant_a, title="A1", status="aperto", priority="media")
    Task.objects.create(plant=plant_b, title="B1", status="aperto", priority="media")
    qs = scope_queryset_by_plant(Task.objects.all(), org_user)
    assert qs.count() == 2


@pytest.mark.django_db
def test_no_access_user_sees_nothing(no_access_user, plant_a):
    from apps.tasks.models import Task
    Task.objects.create(plant=plant_a, title="A1", status="aperto", priority="media")
    qs = scope_queryset_by_plant(Task.objects.all(), no_access_user)
    assert qs.count() == 0


@pytest.mark.django_db
def test_allow_null_plant_includes_unassigned(pm_a, plant_a, plant_b):
    from apps.tasks.models import Task
    Task.objects.create(plant=plant_a, title="A1", status="aperto", priority="media")
    Task.objects.create(plant=plant_b, title="B1", status="aperto", priority="media")
    Task.objects.create(plant=None, title="Global", status="aperto", priority="media")
    qs = scope_queryset_by_plant(Task.objects.all(), pm_a, allow_null_plant=True)
    titles = set(qs.values_list("title", flat=True))
    assert titles == {"A1", "Global"}


@pytest.mark.django_db
def test_extra_plant_ids_union(pm_a, plant_a, plant_b):
    from apps.tasks.models import Task
    Task.objects.create(plant=plant_a, title="A1", status="aperto", priority="media")
    Task.objects.create(plant=plant_b, title="B1", status="aperto", priority="media")
    qs = scope_queryset_by_plant(
        Task.objects.all(), pm_a, extra_plant_ids=[plant_b.id],
    )
    titles = set(qs.values_list("title", flat=True))
    assert titles == {"A1", "B1"}

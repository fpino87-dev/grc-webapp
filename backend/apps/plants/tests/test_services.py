"""P2-1 — copertura services.py del modulo plants (M01).

Copre: get_active_frameworks / get_active_framework_codes, get_nis2_plants,
delete_plant (blocco dipendenze, force non-superuser, cascata force).
"""
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.plants.models import Plant, PlantFramework
from apps.plants.services import (
    delete_plant,
    get_active_framework_codes,
    get_active_frameworks,
    get_nis2_plants,
)

User = get_user_model()


@pytest.fixture
def framework_iso(db):
    from apps.controls.models import Framework

    return Framework.objects.create(
        code="ISO27001", name="ISO 27001:2022", version="2022",
        published_at=datetime.date(2022, 10, 25),
    )


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        username="root", email="root@test.com", password="test-pw-123456",
    )


# ── get_active_frameworks / codes ───────────────────────────────────────────


@pytest.mark.django_db
def test_get_active_frameworks_returns_only_active_for_plant(plant_nis2, framework_iso):
    PlantFramework.objects.create(
        plant=plant_nis2, framework=framework_iso,
        active_from=datetime.date.today(), active=True,
    )
    result = get_active_frameworks(plant_nis2)
    assert list(result) == [framework_iso]


@pytest.mark.django_db
def test_get_active_frameworks_excludes_inactive(plant_nis2, framework_iso):
    PlantFramework.objects.create(
        plant=plant_nis2, framework=framework_iso,
        active_from=datetime.date.today(), active=False,
    )
    assert list(get_active_frameworks(plant_nis2)) == []


@pytest.mark.django_db
def test_get_active_frameworks_excludes_archived(plant_nis2, framework_iso):
    framework_iso.archived_at = datetime.date.today()
    framework_iso.save(update_fields=["archived_at"])
    PlantFramework.objects.create(
        plant=plant_nis2, framework=framework_iso,
        active_from=datetime.date.today(), active=True,
    )
    assert list(get_active_frameworks(plant_nis2)) == []


@pytest.mark.django_db
def test_get_active_frameworks_none_plant_returns_all_non_archived(framework_iso):
    from apps.controls.models import Framework

    archived = Framework.objects.create(
        code="OLD", name="Old", version="1", published_at=datetime.date(2020, 1, 1),
        archived_at=datetime.date(2021, 1, 1),
    )
    result = get_active_frameworks(None)
    assert framework_iso in result
    assert archived not in result


@pytest.mark.django_db
def test_get_active_framework_codes(plant_nis2, framework_iso):
    PlantFramework.objects.create(
        plant=plant_nis2, framework=framework_iso,
        active_from=datetime.date.today(), active=True,
    )
    assert get_active_framework_codes(plant_nis2) == ["ISO27001"]


# ── get_nis2_plants ─────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_get_nis2_plants_filters_by_scope(plant_nis2, plant_tisax):
    importante = Plant.objects.create(
        code="IMP", name="Importante", country="IT",
        nis2_scope="importante", status="attivo",
    )
    result = set(get_nis2_plants())
    assert plant_nis2 in result        # essenziale
    assert importante in result        # importante
    assert plant_tisax not in result   # non_soggetto


@pytest.mark.django_db
def test_get_nis2_plants_excludes_soft_deleted(plant_nis2):
    plant_nis2.soft_delete()
    assert plant_nis2 not in set(get_nis2_plants())


# ── delete_plant: blocco dipendenze ─────────────────────────────────────────


@pytest.mark.django_db
def test_delete_plant_blocks_on_active_dependency(plant_nis2, co_user):
    from apps.assets.models import Asset

    Asset.objects.create(
        plant=plant_nis2, name="Server", asset_type="IT", criticality=3,
    )
    with pytest.raises(ValidationError) as exc:
        delete_plant(plant_nis2, co_user, force=False)
    assert exc.value.code == "blocking_dependencies"
    assert exc.value.params["blocking"]["assets"] == 1
    plant_nis2.refresh_from_db()
    assert plant_nis2.deleted_at is None  # non eliminato


@pytest.mark.django_db
def test_delete_plant_blocks_on_sub_plant(plant_nis2, co_user):
    Plant.objects.create(
        code="SUB", name="Sub", country="IT", nis2_scope="non_soggetto",
        status="attivo", parent_plant=plant_nis2,
    )
    with pytest.raises(ValidationError) as exc:
        delete_plant(plant_nis2, co_user, force=False)
    assert "sub_plants" in exc.value.params["blocking"]


@pytest.mark.django_db
def test_delete_plant_succeeds_without_dependencies(plant_tisax, co_user):
    delete_plant(plant_tisax, co_user, force=False)
    plant_tisax.refresh_from_db()
    assert plant_tisax.deleted_at is not None


# ── delete_plant: force ─────────────────────────────────────────────────────


@pytest.mark.django_db
def test_delete_plant_force_requires_superuser(plant_nis2, co_user):
    with pytest.raises(ValidationError):
        delete_plant(plant_nis2, co_user, force=True)
    plant_nis2.refresh_from_db()
    assert plant_nis2.deleted_at is None


@pytest.mark.django_db
def test_delete_plant_force_cascades_dependencies(plant_nis2, superuser):
    from apps.assets.models import Asset

    asset = Asset.objects.create(
        plant=plant_nis2, name="Server", asset_type="IT", criticality=3,
    )
    sub = Plant.objects.create(
        code="SUB2", name="Sub2", country="IT", nis2_scope="non_soggetto",
        status="attivo", parent_plant=plant_nis2,
    )

    delete_plant(plant_nis2, superuser, force=True)

    plant_nis2.refresh_from_db()
    asset.refresh_from_db()
    sub.refresh_from_db()
    assert plant_nis2.deleted_at is not None
    assert asset.deleted_at is not None
    assert sub.deleted_at is not None


@pytest.mark.django_db
def test_delete_plant_force_writes_audit(plant_tisax, superuser):
    from core.audit import AuditLog

    delete_plant(plant_tisax, superuser, force=True)
    assert AuditLog.objects.filter(action_code="plants.force_delete").exists()

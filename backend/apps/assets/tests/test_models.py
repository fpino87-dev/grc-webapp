"""Test modelli Asset IT/OT — proprietà calcolate."""
import pytest
from datetime import date, timedelta
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="amd_user", email="amd@test.com", password="test")


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="AMD-P", name="Plant AMD", country="IT", nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def network_zone(db, plant, user):
    from apps.assets.models import NetworkZone
    return NetworkZone.objects.create(plant=plant, name="OT", zone_type="OT", created_by=user)


# ── AssetIT.is_eol ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_asset_it_is_eol_when_past(plant, user):
    from apps.assets.models import AssetIT
    a = AssetIT.objects.create(
        plant=plant, name="EOL Asset", asset_type="IT", criticality=1,
        eol_date=date.today() - timedelta(days=1), created_by=user,
    )
    assert a.is_eol is True


@pytest.mark.django_db
def test_asset_it_is_eol_false_when_future(plant, user):
    from apps.assets.models import AssetIT
    a = AssetIT.objects.create(
        plant=plant, name="Future Asset", asset_type="IT", criticality=1,
        eol_date=date.today() + timedelta(days=365), created_by=user,
    )
    assert a.is_eol is False


@pytest.mark.django_db
def test_asset_it_is_eol_false_when_no_date(plant, user):
    from apps.assets.models import AssetIT
    a = AssetIT.objects.create(
        plant=plant, name="No EOL", asset_type="IT", criticality=1,
        eol_date=None, created_by=user,
    )
    assert not a.is_eol


# ── AssetIT.exposure_score ────────────────────────────────────────────────

@pytest.mark.django_db
def test_asset_it_exposure_score_internet_exposed(plant, user):
    from apps.assets.models import AssetIT
    a = AssetIT.objects.create(
        plant=plant, name="Exposed", asset_type="IT", criticality=3,
        internet_exposed=True, created_by=user,
    )
    score = a.exposure_score
    assert score >= 2  # internet exposed adds points


@pytest.mark.django_db
def test_asset_it_exposure_score_eol_increases(plant, user):
    from apps.assets.models import AssetIT
    a_normal = AssetIT.objects.create(
        plant=plant, name="Normal", asset_type="IT", criticality=3,
        eol_date=None, internet_exposed=False, created_by=user,
    )
    a_eol = AssetIT.objects.create(
        plant=plant, name="EOL Exposed", asset_type="IT", criticality=3,
        eol_date=date.today() - timedelta(days=1), created_by=user,
    )
    assert a_eol.exposure_score >= a_normal.exposure_score


# ── AssetOT.isolation_score ───────────────────────────────────────────────

@pytest.mark.django_db
def test_asset_ot_isolation_score_low_purdue(plant, network_zone, user):
    from apps.assets.models import AssetOT
    a = AssetOT.objects.create(
        plant=plant, name="OT Level 1", asset_type="OT", criticality=4,
        purdue_level=1, category="PLC", network_zone=network_zone, created_by=user,
    )
    score = a.isolation_score
    assert isinstance(score, (int, float))


@pytest.mark.django_db
def test_asset_ot_patchable_vs_not(plant, network_zone, user):
    from apps.assets.models import AssetOT
    patchable = AssetOT.objects.create(
        plant=plant, name="Patchable", asset_type="OT", criticality=3,
        purdue_level=2, category="HMI", patchable=True,
        network_zone=network_zone, created_by=user,
    )
    not_patchable = AssetOT.objects.create(
        plant=plant, name="NotPatch", asset_type="OT", criticality=3,
        purdue_level=2, category="HMI", patchable=False,
        network_zone=network_zone, created_by=user,
    )
    # Not patchable is riskier
    assert not_patchable.isolation_score >= patchable.isolation_score


# ── Asset.has_recent_change ───────────────────────────────────────────────

@pytest.mark.django_db
def test_asset_has_recent_change_true(plant, user):
    from apps.assets.models import AssetIT
    a = AssetIT.objects.create(
        plant=plant, name="Changed", asset_type="IT", criticality=2,
        last_change_date=date.today(), created_by=user,
    )
    assert a.has_recent_change is True


@pytest.mark.django_db
def test_asset_has_recent_change_false_when_old(plant, user):
    from apps.assets.models import AssetIT
    old = date.today() - timedelta(days=60)
    a = AssetIT.objects.create(
        plant=plant, name="Old Change", asset_type="IT", criticality=2,
        last_change_date=old, created_by=user,
    )
    assert a.has_recent_change is False

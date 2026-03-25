"""
Test modello TrustedDevice: creazione, verifica, scadenza, revoca.
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="td@test.com", email="td@test.com", password="x")


@pytest.mark.django_db
def test_create_for_user_returns_raw_token(user):
    from apps.auth_grc.models import TrustedDevice
    obj, raw = TrustedDevice.create_for_user(user, device_name="Chrome")
    assert raw  # token grezzo non vuoto
    assert obj.token_hash != raw  # hash ≠ raw
    assert obj.device_name == "Chrome"
    assert obj.expires_at > timezone.now()


@pytest.mark.django_db
def test_verify_valid_token(user):
    from apps.auth_grc.models import TrustedDevice
    _, raw = TrustedDevice.create_for_user(user)
    assert TrustedDevice.verify(user, raw) is True


@pytest.mark.django_db
def test_verify_wrong_token(user):
    from apps.auth_grc.models import TrustedDevice
    TrustedDevice.create_for_user(user)
    assert TrustedDevice.verify(user, "not-the-right-token") is False


@pytest.mark.django_db
def test_verify_empty_token(user):
    from apps.auth_grc.models import TrustedDevice
    assert TrustedDevice.verify(user, "") is False


@pytest.mark.django_db
def test_verify_expired_token(user):
    from apps.auth_grc.models import TrustedDevice
    _, raw = TrustedDevice.create_for_user(user)
    TrustedDevice.objects.filter(user=user).update(
        expires_at=timezone.now() - timezone.timedelta(seconds=1)
    )
    assert TrustedDevice.verify(user, raw) is False


@pytest.mark.django_db
def test_revoke_soft_deletes_device(user):
    from apps.auth_grc.models import TrustedDevice
    obj, raw = TrustedDevice.create_for_user(user)
    obj.revoke()
    # Soft delete: non visibile dal manager default
    assert TrustedDevice.objects.filter(pk=obj.pk).count() == 0
    # Non più verificabile
    assert TrustedDevice.verify(user, raw) is False


@pytest.mark.django_db
def test_multiple_devices_same_user(user):
    from apps.auth_grc.models import TrustedDevice
    _, raw1 = TrustedDevice.create_for_user(user, "Chrome")
    _, raw2 = TrustedDevice.create_for_user(user, "Firefox")
    assert TrustedDevice.verify(user, raw1) is True
    assert TrustedDevice.verify(user, raw2) is True
    assert TrustedDevice.objects.filter(user=user).count() == 2

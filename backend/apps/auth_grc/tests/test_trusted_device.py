"""
Test modello TrustedDevice: creazione, verifica, scadenza, revoca.

newfix S8 — il modello richiede ora un fingerprint del browser (UA +
Accept-Language) sia in `create_for_user` sia in `verify`. Senza match
il device_token non e' utilizzabile.
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


# Fingerprint source di default per i test (UA + Accept-Language).
FP = "Mozilla/5.0 Chrome\x01it-IT,it;q=0.9"
FP_OTHER = "Mozilla/5.0 Firefox\x01en-US,en;q=0.9"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="td@test.com", email="td@test.com", password="x")


@pytest.mark.django_db
def test_create_for_user_returns_raw_token(user):
    from apps.auth_grc.models import TrustedDevice
    obj, raw = TrustedDevice.create_for_user(user, device_name="Chrome", fingerprint_source=FP)
    assert raw  # token grezzo non vuoto
    assert obj.token_hash != raw  # hash ≠ raw
    assert obj.device_name == "Chrome"
    assert obj.expires_at > timezone.now()
    assert obj.fingerprint_hash  # newfix S8: fingerprint salvato


@pytest.mark.django_db
def test_verify_valid_token(user):
    from apps.auth_grc.models import TrustedDevice
    _, raw = TrustedDevice.create_for_user(user, fingerprint_source=FP)
    assert TrustedDevice.verify(user, raw, fingerprint_source=FP) is True


@pytest.mark.django_db
def test_verify_wrong_token(user):
    from apps.auth_grc.models import TrustedDevice
    TrustedDevice.create_for_user(user, fingerprint_source=FP)
    assert TrustedDevice.verify(user, "not-the-right-token", fingerprint_source=FP) is False


@pytest.mark.django_db
def test_verify_empty_token(user):
    from apps.auth_grc.models import TrustedDevice
    assert TrustedDevice.verify(user, "", fingerprint_source=FP) is False


@pytest.mark.django_db
def test_verify_expired_token(user):
    from apps.auth_grc.models import TrustedDevice
    _, raw = TrustedDevice.create_for_user(user, fingerprint_source=FP)
    TrustedDevice.objects.filter(user=user).update(
        expires_at=timezone.now() - timezone.timedelta(seconds=1)
    )
    assert TrustedDevice.verify(user, raw, fingerprint_source=FP) is False


@pytest.mark.django_db
def test_revoke_soft_deletes_device(user):
    from apps.auth_grc.models import TrustedDevice
    obj, raw = TrustedDevice.create_for_user(user, fingerprint_source=FP)
    obj.revoke()
    # Soft delete: non visibile dal manager default
    assert TrustedDevice.objects.filter(pk=obj.pk).count() == 0
    # Non più verificabile
    assert TrustedDevice.verify(user, raw, fingerprint_source=FP) is False


@pytest.mark.django_db
def test_multiple_devices_same_user(user):
    from apps.auth_grc.models import TrustedDevice
    _, raw1 = TrustedDevice.create_for_user(user, "Chrome", fingerprint_source=FP)
    _, raw2 = TrustedDevice.create_for_user(user, "Firefox", fingerprint_source=FP_OTHER)
    assert TrustedDevice.verify(user, raw1, fingerprint_source=FP) is True
    assert TrustedDevice.verify(user, raw2, fingerprint_source=FP_OTHER) is True
    assert TrustedDevice.objects.filter(user=user).count() == 2


# ── newfix S8 — fingerprint binding ──────────────────────────────────────────


@pytest.mark.django_db
def test_verify_rejects_token_from_different_browser(user):
    """Token rubato e replayato da un browser/lingua differenti -> fail."""
    from apps.auth_grc.models import TrustedDevice
    _, raw = TrustedDevice.create_for_user(user, fingerprint_source=FP)
    assert TrustedDevice.verify(user, raw, fingerprint_source=FP_OTHER) is False


@pytest.mark.django_db
def test_verify_rejects_token_without_request_fingerprint(user):
    """Token valido ma request senza UA/lingua (curl, abuso) -> fail."""
    from apps.auth_grc.models import TrustedDevice
    _, raw = TrustedDevice.create_for_user(user, fingerprint_source=FP)
    assert TrustedDevice.verify(user, raw, fingerprint_source="") is False


@pytest.mark.django_db
def test_verify_rejects_legacy_record_without_fingerprint(user):
    """Record pre-S8 con fingerprint_hash="" non sono piu' accettati."""
    from apps.auth_grc.models import TrustedDevice
    obj, raw = TrustedDevice.create_for_user(user, fingerprint_source=FP)
    # Simula un record legacy: cancella il fingerprint_hash dopo la creazione.
    TrustedDevice.objects.filter(pk=obj.pk).update(fingerprint_hash="")
    assert TrustedDevice.verify(user, raw, fingerprint_source=FP) is False


@pytest.mark.django_db
def test_password_change_revokes_all_trusted_devices(user):
    """Cambio password (admin reset / self) -> tutti i TrustedDevice revocati."""
    from apps.auth_grc.models import TrustedDevice
    _, raw1 = TrustedDevice.create_for_user(user, "Chrome", fingerprint_source=FP)
    _, raw2 = TrustedDevice.create_for_user(user, "Firefox", fingerprint_source=FP_OTHER)
    assert TrustedDevice.objects.filter(user=user).count() == 2

    user.set_password("brand-new-password-123!")
    user.save()

    # Tutti soft-deleted, niente più verifica positiva.
    assert TrustedDevice.objects.filter(user=user).count() == 0
    assert TrustedDevice.verify(user, raw1, fingerprint_source=FP) is False
    assert TrustedDevice.verify(user, raw2, fingerprint_source=FP_OTHER) is False


@pytest.mark.django_db
def test_password_unchanged_does_not_revoke_devices(user):
    """save() che non tocca la password non deve azzerare i TrustedDevice."""
    from apps.auth_grc.models import TrustedDevice
    TrustedDevice.create_for_user(user, fingerprint_source=FP)
    # Modifica un campo non-password.
    user.first_name = "Mario"
    user.save()
    assert TrustedDevice.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_revoke_all_for_user_returns_count(user):
    from apps.auth_grc.models import TrustedDevice
    TrustedDevice.create_for_user(user, fingerprint_source=FP)
    TrustedDevice.create_for_user(user, fingerprint_source=FP_OTHER)
    assert TrustedDevice.revoke_all_for_user(user) == 2
    assert TrustedDevice.objects.filter(user=user).count() == 0


@pytest.mark.django_db
def test_compute_fingerprint_uses_pepper(user):
    """Senza il SECRET_KEY del backend l'hash non si ricostruisce."""
    from apps.auth_grc.models import compute_device_fingerprint
    h = compute_device_fingerprint(FP)
    assert len(h) == 64
    # Empty source -> empty hash
    assert compute_device_fingerprint("") == ""

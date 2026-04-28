"""
Test flusso MFA: login → OTP → JWT, device fidato, rate limiting.
"""
import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core import signing
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def user_no_mfa(db):
    return User.objects.create_user(
        username="nomfa@test.com",
        email="nomfa@test.com",
        password="StrongPass123!",
    )


@pytest.fixture
def user_with_mfa(db):
    from django_otp.plugins.otp_totp.models import TOTPDevice
    user = User.objects.create_user(
        username="mfa@test.com",
        email="mfa@test.com",
        password="StrongPass123!",
    )
    TOTPDevice.objects.create(user=user, name="default", confirmed=True)
    return user


# ── Login senza MFA ───────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_login_no_mfa_returns_jwt(user_no_mfa):
    client = APIClient()
    res = client.post("/api/token/", {"username": "nomfa@test.com", "password": "StrongPass123!"})
    assert res.status_code == 200
    assert "access" in res.data
    assert "refresh" in res.data


@pytest.mark.django_db
def test_login_invalid_credentials():
    client = APIClient()
    res = client.post("/api/token/", {"username": "noone@test.com", "password": "wrong"})
    assert res.status_code == 401


# ── Login con MFA attivo ──────────────────────────────────────────────────────

@pytest.mark.django_db
def test_login_mfa_required_returns_202(user_with_mfa):
    client = APIClient()
    res = client.post("/api/token/", {"username": "mfa@test.com", "password": "StrongPass123!"})
    assert res.status_code == 202
    assert res.data["mfa_required"] is True
    assert "mfa_token" in res.data


# ── Verifica OTP ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_mfa_verify_valid_otp_returns_jwt(user_with_mfa):
    client = APIClient()
    # Ottieni mfa_token
    res = client.post("/api/token/", {"username": "mfa@test.com", "password": "StrongPass123!"})
    mfa_token = res.data["mfa_token"]

    # Mock verify_token su tutti i device
    with patch("core.jwt.devices_for_user") as mock_devices:
        mock_device = mock_devices.return_value.__iter__.return_value = iter([type("D", (), {"verify_token": lambda self, c: True})() ])
        mock_devices.return_value = [type("D", (), {"verify_token": lambda self, c: True})()]
        res2 = client.post("/api/token/mfa/", {"mfa_token": mfa_token, "otp_code": "123456"})

    assert res2.status_code == 200
    assert "access" in res2.data


@pytest.mark.django_db
def test_mfa_verify_invalid_otp_returns_401(user_with_mfa):
    client = APIClient()
    res = client.post("/api/token/", {"username": "mfa@test.com", "password": "StrongPass123!"})
    mfa_token = res.data["mfa_token"]

    with patch("core.jwt.devices_for_user") as mock_devices:
        mock_devices.return_value = [type("D", (), {"verify_token": lambda self, c: False})()]
        res2 = client.post("/api/token/mfa/", {"mfa_token": mfa_token, "otp_code": "000000"})

    assert res2.status_code == 401


@pytest.mark.django_db
def test_mfa_verify_expired_token_returns_401(user_with_mfa):
    # Token firmato con TTL -1 (già scaduto)
    expired = signing.dumps(
        {"uid": str(user_with_mfa.pk)},
        salt="grc-mfa-token",
    )
    client = APIClient()
    with patch("core.jwt.signing.loads", side_effect=signing.SignatureExpired):
        res = client.post("/api/token/mfa/", {"mfa_token": expired, "otp_code": "123456"})
    assert res.status_code == 401


@pytest.mark.django_db
def test_mfa_verify_missing_fields_returns_400():
    client = APIClient()
    res = client.post("/api/token/mfa/", {"mfa_token": "x"})  # otp_code mancante
    assert res.status_code == 400


# ── Trust device (bypass MFA 30 giorni) ──────────────────────────────────────

_FP_HEADERS = {
    "HTTP_USER_AGENT": "Mozilla/5.0 PytestBrowser",
    "HTTP_ACCEPT_LANGUAGE": "it-IT,it;q=0.9",
}
_FP_SOURCE = f"{_FP_HEADERS['HTTP_USER_AGENT']}\x01{_FP_HEADERS['HTTP_ACCEPT_LANGUAGE']}"


@pytest.mark.django_db
def test_login_with_valid_device_token_skips_mfa(user_with_mfa):
    from apps.auth_grc.models import TrustedDevice
    _, raw = TrustedDevice.create_for_user(
        user_with_mfa, device_name="Test Browser", fingerprint_source=_FP_SOURCE,
    )

    client = APIClient()
    res = client.post(
        "/api/token/",
        {"username": "mfa@test.com", "password": "StrongPass123!", "device_token": raw},
        **_FP_HEADERS,
    )
    assert res.status_code == 200
    assert "access" in res.data


@pytest.mark.django_db
def test_login_with_expired_device_token_requires_mfa(user_with_mfa):
    from apps.auth_grc.models import TrustedDevice
    from django.utils import timezone

    _, raw = TrustedDevice.create_for_user(user_with_mfa, fingerprint_source=_FP_SOURCE)
    # Scade il token manualmente
    TrustedDevice.objects.filter(user=user_with_mfa).update(
        expires_at=timezone.now() - timezone.timedelta(days=1)
    )

    client = APIClient()
    res = client.post(
        "/api/token/",
        {"username": "mfa@test.com", "password": "StrongPass123!", "device_token": raw},
        **_FP_HEADERS,
    )
    assert res.status_code == 202  # MFA richiesto


@pytest.mark.django_db
def test_login_with_device_token_from_different_browser_requires_mfa(user_with_mfa):
    """newfix S8: device_token rubato e replayato da UA diverso -> MFA."""
    from apps.auth_grc.models import TrustedDevice
    _, raw = TrustedDevice.create_for_user(user_with_mfa, fingerprint_source=_FP_SOURCE)

    client = APIClient()
    res = client.post(
        "/api/token/",
        {"username": "mfa@test.com", "password": "StrongPass123!", "device_token": raw},
        HTTP_USER_AGENT="curl/8.0",
        HTTP_ACCEPT_LANGUAGE="en-US",
    )
    assert res.status_code == 202  # MFA richiesto perche' fingerprint mismatch


@pytest.mark.django_db
def test_mfa_verify_with_trust_device_returns_device_token(user_with_mfa):
    client = APIClient()
    res = client.post("/api/token/", {"username": "mfa@test.com", "password": "StrongPass123!"})
    mfa_token = res.data["mfa_token"]

    with patch("core.jwt.devices_for_user") as mock_devices:
        mock_devices.return_value = [type("D", (), {"verify_token": lambda self, c: True})()]
        res2 = client.post("/api/token/mfa/", {
            "mfa_token": mfa_token,
            "otp_code": "123456",
            "trust_device": True,
        })

    assert res2.status_code == 200
    assert "device_token" in res2.data

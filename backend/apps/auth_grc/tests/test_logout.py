"""
Test logout con blacklist del refresh token (newfix 2026-06-09 #2 + #6).

Dal newfix #6 il refresh token vive nel cookie httpOnly `grc_refresh`:
il logout lo legge dal cookie (fallback body), lo blacklista e cancella
il cookie.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

PASSWORD = "Str0ng-Passw0rd-2026!"


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="logout@azienda.it", email="logout@azienda.it", password=PASSWORD,
    )


@pytest.fixture
def logged_client(user):
    """Client con login reale: Bearer impostato e cookie grc_refresh a bordo."""
    client = APIClient()
    res = client.post("/api/token/", {"username": user.email, "password": PASSWORD})
    assert res.status_code == 200
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    client._refresh_value = res.cookies["grc_refresh"].value
    return client


@pytest.mark.django_db
def test_logout_requires_authentication():
    res = APIClient().post("/api/token/logout/", {"refresh": "x"})
    assert res.status_code == 401


@pytest.mark.django_db
def test_logout_blacklists_cookie_refresh(logged_client):
    refresh_value = logged_client._refresh_value

    res = logged_client.post("/api/token/logout/", {})
    assert res.status_code == 204
    # Il cookie viene cancellato nella risposta
    assert res.cookies["grc_refresh"].value == ""

    # Il refresh blacklistato non deve più emettere access token nemmeno via body
    res2 = APIClient().post("/api/token/refresh/", {"refresh": refresh_value})
    assert res2.status_code == 401


@pytest.mark.django_db
def test_logout_with_body_refresh_still_supported(user):
    """Fallback body per client legacy/machine-to-machine."""
    client = APIClient()
    res = client.post("/api/token/", {"username": user.email, "password": PASSWORD})
    refresh_value = res.cookies["grc_refresh"].value

    bare = APIClient()  # nessun cookie a bordo
    bare.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    out = bare.post("/api/token/logout/", {"refresh": refresh_value})
    assert out.status_code == 204

    res2 = APIClient().post("/api/token/refresh/", {"refresh": refresh_value})
    assert res2.status_code == 401


@pytest.mark.django_db
def test_logout_without_refresh_still_204(user):
    client = APIClient()
    client.force_authenticate(user=user)
    res = client.post("/api/token/logout/", {})
    assert res.status_code == 204


@pytest.mark.django_db
def test_logout_with_garbage_refresh_still_204(user):
    client = APIClient()
    client.force_authenticate(user=user)
    res = client.post("/api/token/logout/", {"refresh": "not-a-jwt"})
    assert res.status_code == 204


@pytest.mark.django_db
def test_logout_writes_audit_log(logged_client):
    from core.audit import AuditLog

    res = logged_client.post("/api/token/logout/", {})
    assert res.status_code == 204

    log = AuditLog.objects.filter(action_code="auth.logout").order_by("-timestamp_utc").first()
    assert log is not None
    assert log.payload.get("refresh_blacklisted") is True

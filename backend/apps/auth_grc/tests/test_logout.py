"""
Test logout con blacklist del refresh token (newfix 2026-06-09 #2).

Il logout deve invalidare il refresh token lato server: senza blacklist
il token resta spendibile per 7 giorni anche dopo la disconnessione.
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
def tokens(user):
    res = APIClient().post(
        "/api/token/", {"username": user.email, "password": PASSWORD},
    )
    assert res.status_code == 200
    return res.data


def _auth_client(access):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return c


@pytest.mark.django_db
def test_logout_requires_authentication():
    res = APIClient().post("/api/token/logout/", {"refresh": "x"})
    assert res.status_code == 401


@pytest.mark.django_db
def test_logout_blacklists_refresh_token(tokens):
    client = _auth_client(tokens["access"])
    res = client.post("/api/token/logout/", {"refresh": tokens["refresh"]})
    assert res.status_code == 204

    # Il refresh blacklistato non deve più emettere access token
    res2 = APIClient().post("/api/token/refresh/", {"refresh": tokens["refresh"]})
    assert res2.status_code == 401


@pytest.mark.django_db
def test_logout_without_refresh_still_204(tokens):
    client = _auth_client(tokens["access"])
    res = client.post("/api/token/logout/", {})
    assert res.status_code == 204


@pytest.mark.django_db
def test_logout_with_garbage_refresh_still_204(tokens):
    client = _auth_client(tokens["access"])
    res = client.post("/api/token/logout/", {"refresh": "not-a-jwt"})
    assert res.status_code == 204


@pytest.mark.django_db
def test_logout_writes_audit_log(tokens, user):
    from core.audit import AuditLog

    client = _auth_client(tokens["access"])
    res = client.post("/api/token/logout/", {"refresh": tokens["refresh"]})
    assert res.status_code == 204

    log = AuditLog.objects.filter(action_code="auth.logout").order_by("-timestamp_utc").first()
    assert log is not None
    assert log.payload.get("refresh_blacklisted") is True

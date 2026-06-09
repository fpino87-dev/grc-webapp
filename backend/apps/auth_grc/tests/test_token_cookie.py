"""
Test refresh token in cookie httpOnly (newfix 2026-06-09 #6).

Il refresh non transita mai nel body delle risposte: login e refresh lo
impostano solo come cookie `grc_refresh` (httpOnly, path /api/token,
SameSite=Strict). Il refresh endpoint lo legge dal cookie con fallback
sul body per client machine-to-machine.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

PASSWORD = "Str0ng-Passw0rd-2026!"


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="cookie@azienda.it", email="cookie@azienda.it", password=PASSWORD,
    )


def _login(client, user):
    res = client.post("/api/token/", {"username": user.email, "password": PASSWORD})
    assert res.status_code == 200
    return res


@pytest.mark.django_db
def test_login_sets_httponly_strict_cookie(user):
    res = _login(APIClient(), user)
    cookie = res.cookies["grc_refresh"]
    assert cookie.value
    assert cookie["httponly"]
    assert cookie["samesite"] == "Strict"
    assert cookie["path"] == "/api/token"
    assert "refresh" not in res.data


@pytest.mark.django_db
def test_refresh_via_cookie_returns_access_and_rotates(user):
    client = APIClient()
    res = _login(client, user)
    first_refresh = res.cookies["grc_refresh"].value

    # Il test client invia automaticamente i cookie ricevuti
    res2 = client.post("/api/token/refresh/", {})
    assert res2.status_code == 200
    assert "access" in res2.data
    assert "refresh" not in res2.data
    # Rotation: il cookie viene riemesso con un token diverso
    rotated = res2.cookies["grc_refresh"].value
    assert rotated and rotated != first_refresh


@pytest.mark.django_db
def test_rotated_old_refresh_is_blacklisted(user):
    client = APIClient()
    res = _login(client, user)
    first_refresh = res.cookies["grc_refresh"].value

    assert client.post("/api/token/refresh/", {}).status_code == 200

    # BLACKLIST_AFTER_ROTATION: il vecchio token non è più spendibile
    res3 = APIClient().post("/api/token/refresh/", {"refresh": first_refresh})
    assert res3.status_code == 401


@pytest.mark.django_db
def test_refresh_without_cookie_or_body_401():
    res = APIClient().post("/api/token/refresh/", {})
    assert res.status_code == 401


@pytest.mark.django_db
def test_refresh_with_invalid_cookie_401_and_cookie_cleared(user):
    client = APIClient()
    client.cookies["grc_refresh"] = "garbage-token"
    res = client.post("/api/token/refresh/", {})
    assert res.status_code == 401
    # Il cookie morto viene rimosso per fermare i replay del client
    assert res.cookies["grc_refresh"].value == ""


@pytest.mark.django_db
def test_refresh_via_body_still_supported(user):
    """Fallback machine-to-machine: refresh nel body JSON."""
    res = _login(APIClient(), user)
    refresh_value = res.cookies["grc_refresh"].value

    res2 = APIClient().post("/api/token/refresh/", {"refresh": refresh_value})
    assert res2.status_code == 200
    assert "access" in res2.data

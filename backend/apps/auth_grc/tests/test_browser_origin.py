"""Browser authentication through a proxy must honor explicit trusted origins."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.mark.django_db
@pytest.mark.parametrize("trusted_setting", ["CORS_ALLOWED_ORIGINS", "CSRF_TRUSTED_ORIGINS"])
def test_login_and_cookie_rotation_from_explicit_trusted_origin(settings, trusted_setting):
    origin = "https://portal.example.test"
    settings.CORS_ALLOWED_ORIGINS = ["http://localhost:3000"]
    settings.CSRF_TRUSTED_ORIGINS = []
    setattr(settings, trusted_setting, [origin])
    password = "Synthetic-Login-Regression-2026!"
    user = get_user_model().objects.create_user(username="origin-test", password=password)
    # Vite rewrites Host to the backend while preserving the browser Origin.
    client = APIClient(HTTP_ORIGIN=origin, HTTP_SEC_FETCH_SITE="same-origin")
    response = client.post("/api/token/", {"username": user.username, "password": password})
    assert response.status_code == 200
    assert "refresh" not in response.data
    cookie = response.cookies["grc_refresh"]
    assert cookie["httponly"]
    assert cookie["samesite"] == "Strict"

    refreshed = client.post("/api/token/refresh/", {})
    assert refreshed.status_code == 200
    assert "access" in refreshed.data
    assert "refresh" not in refreshed.data
    assert refreshed.cookies["grc_refresh"].value != cookie.value


@pytest.mark.parametrize("endpoint", ["/api/token/", "/api/token/refresh/"])
@pytest.mark.parametrize(
    ("origin", "fetch_site"),
    [
        ("https://untrusted.example.test", "same-site"),
        ("https://portal.example.test.attacker.test", "same-site"),
        ("null", "same-origin"),
        ("https://portal.example.test", "cross-site"),
    ],
)
def test_browser_auth_rejects_untrusted_origins(settings, endpoint, origin, fetch_site):
    settings.CORS_ALLOWED_ORIGINS = ["http://localhost:3000"]
    settings.CSRF_TRUSTED_ORIGINS = ["https://portal.example.test"]
    response = APIClient().post(endpoint, {}, HTTP_ORIGIN=origin, HTTP_SEC_FETCH_SITE=fetch_site)
    assert response.status_code == 403

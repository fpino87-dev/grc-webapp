"""Test gating Swagger/OpenAPI (newfix S13)."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
def test_swagger_anonymous_rejected():
    """Anonimo -> 401/403, non 200."""
    client = APIClient()
    res = client.get("/api/docs/")
    assert res.status_code in (401, 403)


@pytest.mark.django_db
def test_schema_anonymous_rejected():
    client = APIClient()
    res = client.get("/api/schema/")
    assert res.status_code in (401, 403)


@pytest.mark.django_db
def test_swagger_non_admin_user_rejected():
    """Utente autenticato ma non staff -> 403."""
    user = User.objects.create_user(username="norm", email="norm@test.com", password="x")
    client = APIClient()
    client.force_authenticate(user=user)
    res = client.get("/api/docs/")
    assert res.status_code == 403


@pytest.mark.django_db
def test_swagger_admin_user_allowed():
    """Utente staff/superuser -> 200."""
    admin = User.objects.create_user(
        username="adm", email="adm@test.com", password="x",
        is_staff=True, is_superuser=True,
    )
    client = APIClient()
    client.force_authenticate(user=admin)
    res = client.get("/api/docs/")
    assert res.status_code == 200

"""Smoke test API Reporting (M18): dopo l'estrazione di services.py le view
restano sottili — qui verifichiamo wiring HTTP + permessi RBAC."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def super_admin(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    user = User.objects.create_user(username="rep_sa@test.com", email="rep_sa@test.com", password="x")
    UserPlantAccess.objects.create(user=user, role=GrcRole.SUPER_ADMIN, scope_type="org")
    return user


@pytest.fixture
def sa_client(super_admin):
    c = APIClient()
    c.force_authenticate(user=super_admin)
    return c


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="REP-API", name="Plant Rep API", country="IT",
        nis2_scope="essenziale", status="attivo",
    )


@pytest.mark.django_db
@pytest.mark.parametrize("path", [
    "/api/v1/reporting/risk/",
    "/api/v1/reporting/incidents/",
    "/api/v1/reporting/compliance/",
    "/api/v1/reporting/dashboard/",
    "/api/v1/reporting/owner-report/",
    "/api/v1/reporting/kpi-trend/",
    "/api/v1/reporting/risk-bia-bcp/",
    "/api/v1/reporting/kpi-overview/",
])
def test_reporting_endpoints_ok(sa_client, plant, path):
    res = sa_client.get(path, {"plant": str(plant.id)})
    assert res.status_code == 200


@pytest.mark.django_db
def test_reporting_requires_auth():
    res = APIClient().get("/api/v1/reporting/dashboard/")
    assert res.status_code in (401, 403)


@pytest.mark.django_db
def test_kpi_suggest_endpoint_ok(sa_client, plant):
    res = sa_client.get("/api/v1/kpi-suggest/", {"plant": str(plant.id), "lang": "it"})
    assert res.status_code == 200
    assert "suggestions" in res.data


@pytest.mark.django_db
def test_external_auditor_can_read_but_not_import_kpi(db, plant):
    """L'auditor esterno legge i report ma NON configura l'ISMS (import KPI)."""
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="rep_ext@test.com", email="rep_ext@test.com", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.EXTERNAL_AUDITOR, scope_type="org")
    c = APIClient()
    c.force_authenticate(user=u)
    # lettura report: ok
    assert c.get("/api/v1/reporting/dashboard/", {"plant": str(plant.id)}).status_code == 200
    # scrittura config KPI: negata
    res = c.post(
        "/api/v1/kpi-suggest/import/",
        {"plant": str(plant.id), "kpi_codes": ["DUMMY"]},
        format="json",
    )
    assert res.status_code == 403

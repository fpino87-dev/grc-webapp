"""Test API incidenti NIS2."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL = "/api/v1/incidents/incidents/"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="inc_user", email="inc@test.com", password="test")


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="INC-P", name="Plant Incidents", country="IT", nis2_scope="essenziale", status="attivo")


@pytest.fixture
def incident(db, plant, user):
    from apps.incidents.models import Incident
    return Incident.objects.create(
        plant=plant,
        title="Test Incident",
        description="Desc",
        detected_at="2026-03-20T10:00:00Z",
        severity="media",
        nis2_notifiable="da_valutare",
        created_by=user,
    )


# ── CRUD ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_incidents_authenticated(client):
    resp = client.get(URL)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_list_incidents_unauthenticated():
    c = APIClient()
    resp = c.get(URL)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_create_incident(client, plant):
    payload = {
        "plant": str(plant.id),
        "title": "Nuovo incidente",
        "description": "Test",
        "detected_at": "2026-03-25T08:00:00Z",
        "severity": "alta",
        "nis2_notifiable": "da_valutare",
        "incident_category": "malicious_code",
    }
    resp = client.post(URL, payload, format="json")
    assert resp.status_code == 201
    assert resp.data["title"] == "Nuovo incidente"
    assert resp.data["severity"] == "alta"


@pytest.mark.django_db
def test_retrieve_incident(client, incident):
    resp = client.get(f"{URL}{incident.id}/")
    assert resp.status_code == 200
    assert resp.data["title"] == "Test Incident"


@pytest.mark.django_db
def test_update_incident_severity(client, incident):
    resp = client.patch(f"{URL}{incident.id}/", {"severity": "critica"}, format="json")
    assert resp.status_code == 200
    assert resp.data["severity"] == "critica"


@pytest.mark.django_db
def test_delete_incident_soft(client, incident):
    resp = client.delete(f"{URL}{incident.id}/")
    assert resp.status_code == 204
    incident.refresh_from_db()
    assert incident.deleted_at is not None


# ── Custom actions ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_confirm_nis2_action(client, incident):
    resp = client.post(f"{URL}{incident.id}/confirm_nis2/", {"nis2_notifiable": "si"}, format="json")
    assert resp.status_code == 200
    incident.refresh_from_db()
    assert incident.nis2_notifiable == "si"


@pytest.mark.django_db
def test_close_incident_without_rca_returns_400(client, incident):
    """Chiusura senza RCA approvato → 400."""
    resp = client.post(f"{URL}{incident.id}/close/", {}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_close_incident_with_approved_rca(client, incident, user):
    from apps.incidents.models import RCA
    from django.utils import timezone
    rca = RCA.objects.create(
        incident=incident,
        summary="Root cause identified",
        approved_at=timezone.now(),
        approved_by=user,
        created_by=user,
    )
    resp = client.post(f"{URL}{incident.id}/close/", {}, format="json")
    assert resp.status_code == 200
    incident.refresh_from_db()
    assert incident.status == "chiuso"


@pytest.mark.django_db
def test_classify_significance_action(client, plant):
    from apps.incidents.models import Incident, NIS2Configuration
    NIS2Configuration.objects.create(
        plant=plant,
        threshold_users=100,
        threshold_hours=4.0,
        threshold_financial=100000,
    )
    inc = Incident.objects.create(
        plant=plant,
        title="NIS2 Classify Test",
        detected_at="2026-03-20T10:00:00Z",
        severity="critica",
        nis2_notifiable="da_valutare",
        service_disruption_hours=8,
        affected_users_count=200,
    )
    resp = client.post(f"{URL}{inc.id}/classify-significance/", {}, format="json")
    assert resp.status_code in (200, 201)


@pytest.mark.django_db
def test_nis2_timeline_action(client, incident):
    resp = client.get(f"{URL}{incident.id}/nis2-timeline/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_filter_by_severity(client, plant, incident):
    from apps.incidents.models import Incident
    Incident.objects.create(
        plant=plant,
        title="Altro",
        detected_at="2026-03-20T10:00:00Z",
        severity="bassa",
        nis2_notifiable="no",
    )
    resp = client.get(f"{URL}?severity=media")
    assert resp.status_code == 200

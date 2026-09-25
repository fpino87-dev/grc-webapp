"""Responsabile dell'azione (testo libero) e data prevista del PDCA: ritardo,
nessun dato personale nell'audit trail, riepilogo nel riesame."""
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

URL = "/api/v1/pdca/cycles/"


@pytest.fixture
def client(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = get_user_model().objects.create_user(username="own_co", email="own_co@test.com", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="OWN", name="Plant OWN", country="IT", nis2_scope="non_soggetto", status="attivo")


@pytest.mark.django_db
def test_owner_and_target_date_editable_and_overdue(client, plant):
    from apps.pdca.services import create_cycle
    from core.audit import AuditLog
    cycle = create_cycle(plant=plant, title="Azione", trigger_type="manual")
    yesterday = (timezone.localdate() - datetime.timedelta(days=1)).isoformat()
    resp = client.patch(f"{URL}{cycle.pk}/", {"action_owner": "HR Manager — OWN", "target_date": yesterday},
                        format="json")
    assert resp.status_code == 200, resp.data
    assert resp.data["action_owner"] == "HR Manager — OWN" and resp.data["is_overdue"] is True
    log = AuditLog.objects.filter(action_code="pdca.cycle.updated", entity_id=cycle.pk).latest("timestamp_utc")
    assert "HR Manager" not in str(log.payload)  # solo i nomi dei campi, non i valori


@pytest.mark.django_db
def test_closed_or_future_cycle_not_overdue(plant):
    from apps.pdca.services import create_cycle
    c = create_cycle(plant=plant, title="Futuro", trigger_type="manual")
    c.target_date = timezone.localdate() + datetime.timedelta(days=5)
    assert c.is_overdue is False
    c.target_date = timezone.localdate() - datetime.timedelta(days=5)
    c.fase_corrente = "archiviato"
    assert c.is_overdue is False


@pytest.mark.django_db
def test_review_snapshot_lists_overdue_cycles(client, plant):
    from apps.management_review.models import ManagementReview
    from apps.management_review.services.snapshot import generate_snapshot
    from apps.pdca.services import create_cycle
    c = create_cycle(plant=plant, title="In ritardo", trigger_type="manual")
    c.action_owner = "IT Manager"
    c.target_date = timezone.localdate() - datetime.timedelta(days=3)
    c.save()
    review = ManagementReview.objects.create(plant=plant, title="Riesame", review_date=timezone.localdate())
    user = get_user_model().objects.create_user(username="own_rev", email="own_rev@test.com", password="x")
    snap = generate_snapshot(review, user)
    assert snap["pdca"]["in_ritardo"] == 1
    assert snap["pdca"]["elenco_in_ritardo"][0]["action_owner"] == "IT Manager"

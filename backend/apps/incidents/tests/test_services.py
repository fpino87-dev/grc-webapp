"""Test services incidenti NIS2."""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="inc_svc", email="incsvc@test.com", password="test")


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="INC-SVC", name="Plant Inc Svc", country="IT",
        nis2_scope="essenziale", status="attivo",
    )


@pytest.fixture
def incident(db, plant, user):
    from apps.incidents.models import Incident
    return Incident.objects.create(
        plant=plant,
        title="Incidente Servizi Test",
        description="Test service",
        detected_at=timezone.now(),
        severity="alta",
        nis2_notifiable="da_valutare",
        created_by=user,
    )


@pytest.mark.django_db
def test_close_incident_service(incident, user):
    from apps.incidents.services import close_incident
    from apps.incidents.models import RCA
    rca = RCA.objects.create(
        incident=incident,
        summary="Root cause found",
        approved_at=timezone.now(),
        approved_by=user,
        created_by=user,
    )
    result = close_incident(incident, user)
    assert result.status == "chiuso"


@pytest.mark.django_db
def test_close_incident_without_rca_raises(incident, user):
    from apps.incidents.services import close_incident
    from rest_framework.exceptions import ValidationError as DRFValidationError
    with pytest.raises(DRFValidationError):
        close_incident(incident, user)

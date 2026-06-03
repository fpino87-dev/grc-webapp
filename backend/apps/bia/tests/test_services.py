"""Test services BIA."""
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="bia_svc", email="biasvc@test.com", password="test")


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="BIA-SVC", name="Plant BIA Svc", country="IT",
        nis2_scope="essenziale", status="attivo",
    )


@pytest.fixture
def process(db, plant, user):
    from apps.bia.models import CriticalProcess
    return CriticalProcess.objects.create(
        plant=plant, name="Processo Test", criticality=4, status="bozza", created_by=user,
    )


@pytest.mark.django_db
def test_validate_process(process, user):
    from apps.bia.services import validate_process
    validate_process(process, user)
    process.refresh_from_db()
    assert process.status == "validato"


@pytest.mark.django_db
def test_approve_process(process, user):
    from apps.bia.services import validate_process, approve_process
    validate_process(process, user)
    approve_process(process, user)
    process.refresh_from_db()
    assert process.status == "approvato"


@pytest.mark.django_db
def test_delete_process_without_dependencies(process, user):
    from apps.bia.services import delete_process
    delete_process(process, user)
    process.refresh_from_db()
    assert process.deleted_at is not None


@pytest.mark.django_db
def test_delete_process_cascade_atomic_rollback(process, user):
    """P1-2: se un audit fallisce a metà cascata, nulla deve restare soft-deleted."""
    from unittest.mock import patch
    from apps.bia.services import delete_process
    from apps.risk.models import RiskAssessment

    ra = RiskAssessment.objects.create(plant=process.plant, critical_process=process, created_by=user)
    # delete_process importa log_action localmente → si patcha alla sorgente.
    with patch("core.audit.log_action", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            delete_process(process, user, cascade=True)
    process.refresh_from_db()
    ra.refresh_from_db()
    assert process.deleted_at is None  # rollback
    assert ra.deleted_at is None

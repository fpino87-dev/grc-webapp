"""Test services PDCA."""
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="pdca_svc", email="pdcasvc@test.com", password="test")


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="PDCA-SVC", name="Plant PDCA Svc", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def cycle(db, plant):
    from apps.pdca.services import create_cycle
    return create_cycle(plant=plant, title="Ciclo Svc", trigger_type="controllo")


@pytest.mark.django_db
def test_create_cycle_service(plant):
    from apps.pdca.services import create_cycle
    cycle = create_cycle(plant=plant, title="Test Ciclo", trigger_type="manuale")
    assert cycle.title == "Test Ciclo"
    assert cycle.fase_corrente == "plan"


@pytest.mark.django_db
def test_advance_phase_plan_to_do(cycle, user):
    from apps.pdca.services import advance_phase
    result = advance_phase(
        cycle, user,
        phase_notes="Piano completato e approvato da tutti i responsabili del progetto",
    )
    assert result.fase_corrente == "do"


@pytest.mark.django_db
def test_advance_phase_short_notes_raises(cycle, user):
    from apps.pdca.services import advance_phase
    from django.core.exceptions import ValidationError
    with pytest.raises(ValidationError):
        advance_phase(cycle, user, phase_notes="Breve")


@pytest.mark.django_db
def test_advance_through_do(cycle, user, plant):
    """Test DO phase requires evidence — check that validation is enforced."""
    from apps.pdca.services import advance_phase
    from django.core.exceptions import ValidationError
    # PLAN → DO succeeds
    advance_phase(cycle, user, phase_notes="Piano completato e approvato da tutti i responsabili")
    # DO → CHECK requires evidence
    with pytest.raises(ValidationError):
        advance_phase(cycle, user, phase_notes="Esecuzione completata correttamente bene")

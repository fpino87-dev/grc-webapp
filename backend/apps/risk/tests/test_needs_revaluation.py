"""Regressione: flag needs_revaluation su edit/complete.

Prima:
- l'update marcava needs_revaluation in base alle CHIAVI del payload (non al
  cambio reale di valore) → un risalvataggio del form rimetteva il rischio
  "da rivalutare" anche senza modifiche;
- "Completa" NON azzerava il flag → un rischio modificato restava segnalato
  per sempre (a meno di rinnovo accettazione, valido solo per gli accettati).
"""
import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def super_admin(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    user = User.objects.create_user(username="nr@test.com", email="nr@test.com", password="x")
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
    return Plant.objects.create(code="NR-P", name="Plant NR", country="IT",
                                nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def assessment(db, plant, super_admin):
    from apps.risk.models import RiskAssessment
    return RiskAssessment.objects.create(
        plant=plant, name="Rischio NR", assessment_type="IT",
        threat_category="malware_ransomware", probability=3, impact=4,
        status="completato", created_by=super_admin,
    )


@pytest.mark.django_db
def test_resave_without_score_change_does_not_flag(sa_client, assessment):
    """Risalvataggio che reinvia probability/impact INVARIATI → niente flag."""
    res = sa_client.patch(
        f"/api/v1/risk/assessments/{assessment.pk}/",
        {"name": "Rischio NR (rinominato)",
         "probability": assessment.probability, "impact": assessment.impact},
        format="json",
    )
    assert res.status_code == 200, res.content
    assessment.refresh_from_db()
    assert assessment.needs_revaluation is False


@pytest.mark.django_db
def test_change_probability_flags_revaluation(sa_client, assessment):
    """Cambio reale di probability → needs_revaluation=True."""
    res = sa_client.patch(
        f"/api/v1/risk/assessments/{assessment.pk}/",
        {"probability": assessment.probability + 1},
        format="json",
    )
    assert res.status_code == 200, res.content
    assessment.refresh_from_db()
    assert assessment.needs_revaluation is True


@pytest.mark.django_db
def test_complete_clears_revaluation_flag(sa_client, assessment):
    """Ri-eseguire 'Completa' chiude il flag da rivalutare."""
    assessment.needs_revaluation = True
    assessment.needs_revaluation_since = timezone.localdate()
    assessment.save(update_fields=["needs_revaluation", "needs_revaluation_since"])

    res = sa_client.post(f"/api/v1/risk/assessments/{assessment.pk}/complete/")
    assert res.status_code == 200, res.content
    assessment.refresh_from_db()
    assert assessment.needs_revaluation is False
    assert assessment.needs_revaluation_since is None

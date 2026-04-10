"""
Test proprietà modelli Risk: risk_level, weighted_score, RiskAppetitePolicy.is_active.
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="RISK-P", name="Plant Risk", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


def make_assessment(plant, prob, impact, **kwargs):
    from apps.risk.models import RiskAssessment
    return RiskAssessment.objects.create(
        plant=plant,
        name="Test",
        assessment_type="IT",
        probability=prob,
        impact=impact,
        **kwargs,
    )


# ── risk_level ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_risk_level_verde(plant):
    # prob=1, impact=1 → score=1 → verde (≤7)
    a = make_assessment(plant, 1, 1)
    assert a.risk_level == "verde"


@pytest.mark.django_db
def test_risk_level_border_verde(plant):
    # prob=1, impact=7 sarebbe score=7 → verde
    # prob=1, impact=7 non esiste (max 5), usiamo 1×7 → non possibile
    # prob=3, impact=2 → score=6 → verde
    a = make_assessment(plant, 3, 2)
    assert a.risk_level == "verde"


@pytest.mark.django_db
def test_risk_level_giallo(plant):
    # prob=2, impact=4 → score=8 → giallo (8-14)
    a = make_assessment(plant, 2, 4)
    assert a.risk_level == "giallo"


@pytest.mark.django_db
def test_risk_level_giallo_border(plant):
    # prob=2, impact=7 → non esiste, usiamo 2×7 che supera scala
    # prob=4, impact=3 → score=12 → giallo
    a = make_assessment(plant, 4, 3)
    assert a.risk_level == "giallo"


@pytest.mark.django_db
def test_risk_level_rosso(plant):
    # prob=5, impact=5 → score=25 → rosso (>14)
    a = make_assessment(plant, 5, 5)
    assert a.risk_level == "rosso"


@pytest.mark.django_db
def test_risk_level_none_when_no_score(plant):
    from apps.risk.models import RiskAssessment
    a = RiskAssessment.objects.create(plant=plant, name="No score", assessment_type="IT")
    assert a.risk_level is None


# ── score calculation via save() ──────────────────────────────────────────────

@pytest.mark.django_db
def test_score_auto_calculated_on_save(plant):
    a = make_assessment(plant, 3, 4)
    assert a.score == 12  # 3 × 4


@pytest.mark.django_db
def test_inherent_score_auto_calculated(plant):
    a = make_assessment(plant, 2, 3, inherent_probability=4, inherent_impact=5)
    assert a.inherent_score == 20  # 4 × 5


# ── RiskAppetitePolicy.is_active ──────────────────────────────────────────────

@pytest.mark.django_db
def test_risk_appetite_policy_is_active(plant):
    from apps.risk.models import RiskAppetitePolicy
    from datetime import date, timedelta
    today = date.today()
    policy = RiskAppetitePolicy.objects.create(
        plant=plant,
        framework_code="ISO27K",
        max_acceptable_score=12,
        valid_from=today - timedelta(days=1),
        valid_until=today + timedelta(days=30),
    )
    assert policy.is_active is True


@pytest.mark.django_db
def test_risk_appetite_policy_expired(plant):
    from apps.risk.models import RiskAppetitePolicy
    from datetime import date, timedelta
    today = date.today()
    policy = RiskAppetitePolicy.objects.create(
        plant=plant,
        framework_code="ISO27K",
        max_acceptable_score=12,
        valid_from=today - timedelta(days=60),
        valid_until=today - timedelta(days=1),
    )
    assert policy.is_active is False


@pytest.mark.django_db
def test_risk_appetite_policy_future(plant):
    from apps.risk.models import RiskAppetitePolicy
    from datetime import date, timedelta
    today = date.today()
    policy = RiskAppetitePolicy.objects.create(
        plant=plant,
        framework_code="ISO27K",
        max_acceptable_score=12,
        valid_from=today + timedelta(days=5),
        valid_until=today + timedelta(days=60),
    )
    assert policy.is_active is False

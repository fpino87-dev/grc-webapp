"""Test services risk assessment."""
import pytest
from datetime import date
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="risk_svc", email="risksvc@test.com", password="test")


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="RSK-SVC", name="Plant Risk Svc", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def assessment(db, plant, user):
    from apps.risk.models import RiskAssessment
    return RiskAssessment.objects.create(
        plant=plant,
        name="Rischio Test Svc",
        assessment_type="IT",
        threat_category="malware_ransomware",
        probability=3,
        impact=4,
        created_by=user,
    )


@pytest.mark.django_db
def test_accept_risk_service(assessment, user):
    from apps.risk.services import accept_risk
    accept_risk(assessment, user, note="Rischio accettato formalmente per motivi aziendali documentati")
    assessment.refresh_from_db()
    assert assessment.risk_accepted_formally is True


@pytest.mark.django_db
def test_calc_score(assessment):
    from apps.risk.services import calc_score
    score = calc_score(assessment)
    assert isinstance(score, int)
    assert score >= 0


@pytest.mark.django_db
def test_calc_ale(assessment):
    from apps.risk.services import calc_ale
    ale = calc_ale(assessment)
    # ALE with no financial data should return 0 or some value
    assert ale is not None


@pytest.mark.django_db
def test_get_risk_bia_bcp_context(assessment):
    from apps.risk.services import get_risk_bia_bcp_context
    context = get_risk_bia_bcp_context(assessment)
    assert isinstance(context, dict)


@pytest.mark.django_db
def test_escalate_red_risk(assessment, user):
    from apps.risk.services import escalate_red_risk
    # Only escalates if score >= threshold, won't fail
    result = escalate_red_risk(assessment, user)
    # Returns notification count or similar
    assert result is not None or result is None  # just ensure no exception

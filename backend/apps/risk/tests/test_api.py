"""
Test API Risk Assessment: CRUD, complete action, accept action.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def super_admin(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    user = User.objects.create_user(username="sa@test.com", email="sa@test.com", password="x")
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
        code="RA-P", name="Plant RA", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def assessment(db, plant, super_admin):
    from apps.risk.models import RiskAssessment
    return RiskAssessment.objects.create(
        plant=plant,
        name="Rischio test",
        assessment_type="IT",
        threat_category="malware_ransomware",
        probability=3,
        impact=4,
        created_by=super_admin,
    )


@pytest.mark.django_db
def test_list_risk_assessments(sa_client):
    res = sa_client.get("/api/v1/risk/assessments/")
    assert res.status_code == 200


@pytest.mark.django_db
def test_create_risk_assessment(sa_client, plant):
    res = sa_client.post("/api/v1/risk/assessments/", {
        "plant": str(plant.pk),
        "name": "Nuovo rischio",
        "assessment_type": "IT",
        "threat_category": "data_breach",
        "probability": 2,
        "impact": 3,
    })
    assert res.status_code == 201
    assert res.data["score"] == 6


@pytest.mark.django_db
def test_create_risk_assessment_unauthenticated(plant):
    client = APIClient()
    res = client.post("/api/v1/risk/assessments/", {
        "plant": str(plant.pk),
        "name": "x",
        "assessment_type": "IT",
    })
    assert res.status_code == 401


@pytest.mark.django_db
def test_retrieve_risk_assessment(sa_client, assessment):
    res = sa_client.get(f"/api/v1/risk/assessments/{assessment.pk}/")
    assert res.status_code == 200
    assert res.data["name"] == "Rischio test"


@pytest.mark.django_db
def test_risk_level_in_response(sa_client, assessment):
    res = sa_client.get(f"/api/v1/risk/assessments/{assessment.pk}/")
    assert res.status_code == 200
    # prob=3, impact=4 → score=12 → giallo
    assert res.data["risk_level"] == "giallo"


@pytest.mark.django_db
def test_delete_assessment_soft(sa_client, assessment):
    res = sa_client.delete(f"/api/v1/risk/assessments/{assessment.pk}/")
    assert res.status_code in (200, 204)
    # Soft delete: non più visibile
    res2 = sa_client.get(f"/api/v1/risk/assessments/{assessment.pk}/")
    assert res2.status_code == 404


# ── RBAC plant scoping (S1) ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_plant_manager_does_not_see_risk_of_other_plant(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    from apps.plants.models import Plant
    from apps.risk.models import RiskAssessment

    plant_a = Plant.objects.create(
        code="RA-SC-A", name="A", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )
    plant_b = Plant.objects.create(
        code="RA-SC-B", name="B", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )
    RiskAssessment.objects.create(
        plant=plant_a, name="Risk A", assessment_type="IT",
        threat_category="malware_ransomware", probability=2, impact=3,
    )
    RiskAssessment.objects.create(
        plant=plant_b, name="Risk B", assessment_type="IT",
        threat_category="malware_ransomware", probability=2, impact=3,
    )
    pm = User.objects.create_user(username="pm_a_risk", email="pmrisk@test", password="x")
    access = UserPlantAccess.objects.create(
        user=pm, role=GrcRole.PLANT_MANAGER, scope_type="single_plant",
    )
    access.scope_plants.set([plant_a])

    c = APIClient()
    c.force_authenticate(user=pm)
    resp = c.get("/api/v1/risk/assessments/")
    assert resp.status_code == 200
    names = {item["name"] for item in resp.data["results"]}
    assert names == {"Risk A"}

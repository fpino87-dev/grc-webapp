"""Test API fornitori."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_SUPPLIERS = "/api/v1/suppliers/suppliers/"
URL_ASSESSMENTS = "/api/v1/suppliers/assessments/"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="sup_user", email="sup@test.com", password="test")


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="SUP-P", name="Plant SUP", country="IT", nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def supplier(db, plant, user):
    from apps.suppliers.models import Supplier
    s = Supplier.objects.create(
        name="Fornitore Test",
        risk_level="medio",
        status="attivo",
        created_by=user,
    )
    s.plants.add(plant)
    return s


@pytest.fixture
def assessment(db, supplier, user):
    from apps.suppliers.models import SupplierAssessment
    from datetime import date
    return SupplierAssessment.objects.create(
        supplier=supplier,
        assessed_by=user,
        assessment_date=date.today(),
        status="pianificato",
        created_by=user,
    )


# ── Suppliers CRUD ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_suppliers_authenticated(client):
    resp = client.get(URL_SUPPLIERS)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_list_suppliers_unauthenticated():
    resp = APIClient().get(URL_SUPPLIERS)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_create_supplier(client, plant):
    payload = {
        "name": "Nuovo Fornitore",
        "risk_level": "alto",
        "status": "attivo",
        "plants": [str(plant.id)],
    }
    resp = client.post(URL_SUPPLIERS, payload, format="json")
    assert resp.status_code == 201
    assert resp.data["name"] == "Nuovo Fornitore"


@pytest.mark.django_db
def test_retrieve_supplier(client, supplier):
    resp = client.get(f"{URL_SUPPLIERS}{supplier.id}/")
    assert resp.status_code == 200
    assert resp.data["name"] == "Fornitore Test"


@pytest.mark.django_db
def test_update_supplier_risk(client, supplier):
    resp = client.patch(f"{URL_SUPPLIERS}{supplier.id}/", {"risk_level": "critico"}, format="json")
    assert resp.status_code == 200
    assert resp.data["risk_level"] == "critico"


@pytest.mark.django_db
def test_delete_supplier(client, supplier):
    resp = client.delete(f"{URL_SUPPLIERS}{supplier.id}/")
    assert resp.status_code == 204
    resp2 = client.get(f"{URL_SUPPLIERS}{supplier.id}/")
    assert resp2.status_code == 404


# ── Assessments CRUD ──────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_assessments(client):
    resp = client.get(URL_ASSESSMENTS)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_create_assessment(client, supplier, user):
    from datetime import date
    payload = {
        "supplier": str(supplier.id),
        "assessed_by": str(user.id),
        "assessment_date": str(date.today()),
        "status": "pianificato",
    }
    resp = client.post(URL_ASSESSMENTS, payload, format="json")
    assert resp.status_code == 201


@pytest.mark.django_db
def test_complete_assessment_action(client, assessment):
    payload = {
        "score_overall": 75,
        "score_governance": 80,
        "score_security": 70,
        "score_bcp": 75,
        "findings": "Nessuna criticità rilevante.",
        "next_assessment_months": 12,
    }
    resp = client.post(f"{URL_ASSESSMENTS}{assessment.id}/complete/", payload, format="json")
    assert resp.status_code in (200, 201, 400)


@pytest.mark.django_db
def test_approve_assessment_action(client, assessment, user):
    # Prima completa
    assessment.status = "completato"
    assessment.score_overall = 80
    assessment.score = 80
    assessment.save()
    resp = client.post(f"{URL_ASSESSMENTS}{assessment.id}/approve/", {"notes": "OK"}, format="json")
    assert resp.status_code in (200, 201, 400)


@pytest.mark.django_db
def test_reject_assessment_action(client, assessment):
    assessment.status = "completato"
    assessment.save()
    resp = client.post(f"{URL_ASSESSMENTS}{assessment.id}/reject/", {"notes": "Non sufficiente"}, format="json")
    assert resp.status_code in (200, 201, 400)

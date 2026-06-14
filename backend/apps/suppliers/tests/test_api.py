"""Test API fornitori."""
import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_SUPPLIERS = "/api/v1/suppliers/suppliers/"
URL_ASSESSMENTS = "/api/v1/suppliers/assessments/"


@pytest.fixture
def user(db):
    """Utente con scope org (vede tutti i fornitori)."""
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="sup_user", email="sup@test.com", password="test")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


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
    return SupplierAssessment.objects.create(
        supplier=supplier,
        assessed_by=user,
        assessment_date=timezone.localdate(),
        status="pianificato",
        created_by=user,
    )


# ── Governance / scoping (M14 review) ─────────────────────────────────────

@pytest.mark.django_db
def test_cannot_fake_assessment_approval_via_patch(client, assessment):
    """status/score sono governati da complete/approve: non via PATCH diretta."""
    resp = client.patch(
        f"{URL_ASSESSMENTS}{assessment.id}/",
        {"status": "approvato", "score_overall": 90},
        format="json",
    )
    assert resp.status_code == 200
    assessment.refresh_from_db()
    assert assessment.status == "pianificato"
    assert assessment.score_overall is None


@pytest.mark.django_db
def test_export_csv_respects_plant_scope(db, plant, supplier):
    """Un utente di un altro sito non vede il fornitore nell'export CSV."""
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    from apps.plants.models import Plant
    other = Plant.objects.create(code="SUP-OTH", name="Other", country="IT",
                                 nis2_scope="non_soggetto", status="attivo")
    pm = User.objects.create_user(username="pm_sup", email="pm_sup@test.com", password="x")
    acc = UserPlantAccess.objects.create(user=pm, role=GrcRole.PLANT_MANAGER, scope_type="single_plant")
    acc.scope_plants.set([other])
    c = APIClient()
    c.force_authenticate(user=pm)
    resp = c.get(f"{URL_SUPPLIERS}export-csv/")
    assert resp.status_code == 200
    assert "Fornitore Test" not in resp.content.decode("utf-8")


@pytest.mark.django_db
def test_send_questionnaire_blocked_cross_plant(db, plant, supplier):
    """Inviare un questionario a un fornitore fuori perimetro è negato."""
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    from apps.plants.models import Plant
    from apps.suppliers.models import QuestionnaireTemplate
    other = Plant.objects.create(code="SUP-O2", name="Other2", country="IT",
                                 nis2_scope="non_soggetto", status="attivo")
    pm = User.objects.create_user(username="pm_sup2", email="pm_sup2@test.com", password="x")
    acc = UserPlantAccess.objects.create(user=pm, role=GrcRole.PLANT_MANAGER, scope_type="single_plant")
    acc.scope_plants.set([other])
    tpl = QuestionnaireTemplate.objects.create(name="T", subject="S", body="B", form_url="https://x.it")
    c = APIClient()
    c.force_authenticate(user=pm)
    resp = c.post(
        "/api/v1/suppliers/questionnaires/send/",
        {"supplier_id": str(supplier.id), "template_id": str(tpl.id)},
        format="json",
    )
    assert resp.status_code == 403


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
    payload = {
        "supplier": str(supplier.id),
        "assessed_by": str(user.id),
        "assessment_date": str(timezone.localdate()),
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


# ── RBAC plant scoping (S1) ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_plant_manager_does_not_see_supplier_of_other_plant(db):
    """PM A non vede fornitori legati esclusivamente a Plant B."""
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    from apps.plants.models import Plant
    from apps.suppliers.models import Supplier

    plant_a = Plant.objects.create(
        code="SUP-A", name="A", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )
    plant_b = Plant.objects.create(
        code="SUP-B", name="B", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )
    sup_a = Supplier.objects.create(name="OnlyA", risk_level="medio", status="attivo")
    sup_a.plants.add(plant_a)
    sup_b = Supplier.objects.create(name="OnlyB", risk_level="medio", status="attivo")
    sup_b.plants.add(plant_b)
    Supplier.objects.create(
        name="Global", risk_level="basso", status="attivo",
    )  # nessun plant → cross-plant

    pm_a = User.objects.create_user(username="pm_a_sup", email="pmasup@test", password="x")
    access = UserPlantAccess.objects.create(
        user=pm_a, role=GrcRole.PLANT_MANAGER, scope_type="single_plant",
    )
    access.scope_plants.set([plant_a])

    c = APIClient()
    c.force_authenticate(user=pm_a)
    resp = c.get(URL_SUPPLIERS)
    assert resp.status_code == 200
    names = {item["name"] for item in resp.data["results"]}
    assert "OnlyA" in names
    assert "OnlyB" not in names
    assert "Global" in names  # cross-plant supplier visibile


@pytest.mark.django_db
def test_plant_manager_cannot_retrieve_supplier_of_other_plant(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    from apps.plants.models import Plant
    from apps.suppliers.models import Supplier

    plant_a = Plant.objects.create(
        code="SUP-RA", name="A", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )
    plant_b = Plant.objects.create(
        code="SUP-RB", name="B", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )
    sup_b = Supplier.objects.create(name="ForbiddenB", risk_level="medio", status="attivo")
    sup_b.plants.add(plant_b)

    pm_a = User.objects.create_user(username="pm_ra_sup", email="pmra@test", password="x")
    access = UserPlantAccess.objects.create(
        user=pm_a, role=GrcRole.PLANT_MANAGER, scope_type="single_plant",
    )
    access.scope_plants.set([plant_a])

    c = APIClient()
    c.force_authenticate(user=pm_a)
    resp = c.get(f"{URL_SUPPLIERS}{sup_b.id}/")
    assert resp.status_code == 404

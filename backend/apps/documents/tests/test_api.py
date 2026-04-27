"""Test API documenti."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_DOCS = "/api/v1/documents/documents/"
URL_EVIDENCES = "/api/v1/documents/evidences/"


@pytest.fixture
def user(db):
    """Utente con scope org (vede tutti i documenti)."""
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="doc_user", email="doc@test.com", password="test")
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
    return Plant.objects.create(
        code="DOC-P", name="Plant DOC", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def document(db, plant, user):
    from apps.documents.models import Document
    return Document.objects.create(
        title="Policy Sicurezza",
        category="policy",
        document_type="policy",
        status="bozza",
        plant=plant,
        created_by=user,
    )


# ── Documents ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_documents_authenticated(client):
    resp = client.get(URL_DOCS)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_list_documents_unauthenticated():
    resp = APIClient().get(URL_DOCS)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_create_document(client, plant):
    payload = {
        "title": "Procedura Backup",
        "category": "procedura",
        "document_type": "procedura",
        "status": "bozza",
        "plant": str(plant.id),
    }
    resp = client.post(URL_DOCS, payload, format="json")
    assert resp.status_code == 201
    assert resp.data["title"] == "Procedura Backup"


@pytest.mark.django_db
def test_retrieve_document(client, document):
    resp = client.get(f"{URL_DOCS}{document.id}/")
    assert resp.status_code == 200
    assert resp.data["title"] == "Policy Sicurezza"


@pytest.mark.django_db
def test_update_document_status(client, document):
    resp = client.patch(f"{URL_DOCS}{document.id}/", {"status": "revisione"}, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "revisione"


@pytest.mark.django_db
def test_delete_document(client, document):
    resp = client.delete(f"{URL_DOCS}{document.id}/")
    assert resp.status_code == 204


@pytest.mark.django_db
def test_filter_documents_by_plant(client, plant, document):
    resp = client.get(f"{URL_DOCS}?plant={plant.id}")
    assert resp.status_code == 200
    ids = [d["id"] for d in resp.data["results"]] if "results" in resp.data else [d["id"] for d in resp.data]
    assert str(document.id) in ids


@pytest.mark.django_db
def test_filter_documents_by_status(client, document):
    resp = client.get(f"{URL_DOCS}?status=bozza")
    assert resp.status_code == 200


# ── Evidences ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_evidences(client):
    resp = client.get(URL_EVIDENCES)
    assert resp.status_code == 200


# ── RBAC plant scoping (S1) ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_pm_does_not_see_documents_of_other_plant(db):
    """PM A vede documenti di Plant A + condivisi con A + org-wide; non vede solo Plant B."""
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    from apps.documents.models import Document
    from apps.plants.models import Plant

    plant_a = Plant.objects.create(
        code="DOC-A", name="A", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )
    plant_b = Plant.objects.create(
        code="DOC-B", name="B", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )
    Document.objects.create(plant=plant_a, title="Doc A", category="policy", status="bozza")
    Document.objects.create(plant=plant_b, title="Doc B", category="policy", status="bozza")
    Document.objects.create(plant=None, title="Doc Global", category="policy", status="bozza")
    shared = Document.objects.create(plant=plant_b, title="Doc Shared", category="policy", status="bozza")
    shared.shared_plants.add(plant_a)

    pm = User.objects.create_user(username="pm_doc", email="pmdoc@test", password="x")
    access = UserPlantAccess.objects.create(
        user=pm, role=GrcRole.PLANT_MANAGER, scope_type="single_plant",
    )
    access.scope_plants.set([plant_a])

    c = APIClient()
    c.force_authenticate(user=pm)
    resp = c.get(URL_DOCS)
    assert resp.status_code == 200
    titles = {item["title"] for item in resp.data["results"]}
    assert "Doc A" in titles
    assert "Doc Global" in titles
    assert "Doc Shared" in titles
    assert "Doc B" not in titles

"""Test API documenti."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_DOCS = "/api/v1/documents/documents/"
URL_EVIDENCES = "/api/v1/documents/evidences/"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="doc_user", email="doc@test.com", password="test")


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

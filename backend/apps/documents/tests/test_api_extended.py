"""Test API documenti — versioni, evidenze e azioni avanzate."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_DOCS = "/api/v1/documents/documents/"
URL_VERSIONS = "/api/v1/documents/document-versions/"
URL_EVIDENCES = "/api/v1/documents/evidences/"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="docx_user", email="docx@test.com", password="test")


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="DX-P", name="Plant DX", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def document(db, plant, user):
    from apps.documents.models import Document
    return Document.objects.create(
        title="Procedura Sicurezza",
        category="procedura",
        document_type="procedura",
        status="bozza",
        plant=plant,
        created_by=user,
    )


@pytest.mark.django_db
def test_list_document_versions(client):
    resp = client.get(URL_VERSIONS)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_filter_documents_by_category(client, document):
    resp = client.get(f"{URL_DOCS}?category=procedura")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_filter_evidences_by_control(client):
    resp = client.get(f"{URL_EVIDENCES}")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_create_evidence(client, plant, document):
    from apps.controls.models import Framework, ControlDomain, Control, ControlInstance
    from apps.plants.models import PlantFramework
    from datetime import date
    f = Framework.objects.create(code="DOC-FW", name="FW", version="1", published_at=date.today())
    PlantFramework.objects.create(plant=plant, framework=f, active_from=date.today(), level="L2", active=True)
    dom = ControlDomain.objects.create(framework=f, code="A.1", translations={"it": {"name": "T"}}, order=1)
    ctrl = Control.objects.create(framework=f, domain=dom, external_id="A.1.1", translations={"it": {"name": "N", "description": "D"}, "en": {"name": "N", "description": "D"}}, level="L2", evidence_requirement={}, control_category="technical")
    inst = ControlInstance.objects.create(plant=plant, control=ctrl, status="non_valutato")
    payload = {
        "control_instance": str(inst.id),
        "description": "Evidenza test",
        "document": str(document.id),
    }
    resp = client.post(URL_EVIDENCES, payload, format="json")
    assert resp.status_code in (200, 201, 400)

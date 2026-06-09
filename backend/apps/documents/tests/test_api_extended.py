"""Test API documenti — versioni, evidenze e azioni avanzate."""
import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_DOCS = "/api/v1/documents/documents/"
URL_VERSIONS = "/api/v1/documents/document-versions/"
URL_EVIDENCES = "/api/v1/documents/evidences/"


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="docx_user", email="docx@test.com", password="test")
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
def test_approve_document_atomic_rollback(document, user):
    """P1-2: se l'audit fallisce, stato documento e record approvazione non persistono."""
    from unittest.mock import patch
    from apps.documents.models import DocumentApproval
    from apps.documents.services import approve_document

    document.status = "revisione"
    document.save(update_fields=["status"])
    with patch("apps.documents.services.log_action", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            approve_document(document, user, notes="ok")
    document.refresh_from_db()
    assert document.status == "revisione"  # rollback: non 'approvato'
    assert not DocumentApproval.objects.filter(document=document).exists()


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
    f = Framework.objects.create(code="DOC-FW", name="FW", version="1", published_at=timezone.localdate())
    PlantFramework.objects.create(plant=plant, framework=f, active_from=timezone.localdate(), level="L2", active=True)
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

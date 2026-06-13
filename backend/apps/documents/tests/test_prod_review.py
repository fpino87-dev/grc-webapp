"""Review prod-readiness M07 (2026-06-13).

DocumentVersionViewSet eliminava le versioni con HARD delete senza audit:
perdita dello storico documentale. Ora soft delete + audit; la creazione di una
versione è ora tracciata.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.auth_grc.models import GrcRole, UserPlantAccess

User = get_user_model()


@pytest.fixture
def admin_client(db):
    u = User.objects.create_user(username="m7admin", email="m7@a.test", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    c = APIClient()
    c.force_authenticate(user=u)
    return u, c


@pytest.fixture
def document(db):
    from apps.documents.models import Document
    from apps.plants.models import Plant
    plant = Plant.objects.create(code="M7P", name="M7 Plant", country="IT",
                                 nis2_scope="importante", status="attivo")
    return Document.objects.create(plant=plant, title="Doc", document_code="DOC-M7",
                                   category="politica", document_type="policy", status="bozza")


@pytest.mark.django_db
def test_document_version_delete_is_soft_and_audited(admin_client, document):
    from apps.documents.models import DocumentVersion
    from core.audit import AuditLog
    user, client = admin_client
    v = DocumentVersion.objects.create(
        document=document, version_number=1, file_name="f.pdf",
        sha256="a" * 64, storage_path="docs/f.pdf", uploaded_by=user,
    )
    resp = client.delete(f"/api/v1/documents/document-versions/{v.id}/")
    assert resp.status_code == 204
    v.refresh_from_db()
    assert v.deleted_at is not None
    assert not DocumentVersion.objects.filter(pk=v.id).exists()
    assert AuditLog.objects.filter(action_code="documents.document_version.delete").exists()

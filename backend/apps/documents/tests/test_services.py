"""P2-1 — copertura documents/services.py (workflow stati, versioni, scadenze, delete)."""
import datetime
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="doc", email="doc@x.it", password="x")


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(username="su", email="su@x.it", password="x")


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="DOC-P", name="Plant Doc", country="IT",
                                nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def document(db, plant, user):
    from apps.documents.models import Document
    return Document.objects.create(
        title="Procedura", category="procedura", document_type="procedura",
        status="bozza", plant=plant, created_by=user,
    )


def test_submit_for_review(document, user):
    from apps.documents.services import submit_for_review
    submit_for_review(document, user)
    document.refresh_from_db()
    assert document.status == "revisione"


def test_approve_document_creates_approval(document, user):
    from apps.documents.models import DocumentApproval
    from apps.documents.services import approve_document
    document.status = "revisione"
    document.save(update_fields=["status"])
    approve_document(document, user, notes="ok")
    document.refresh_from_db()
    assert document.status == "approvato"
    assert document.approver == user
    assert DocumentApproval.objects.filter(document=document, action="approve").exists()


def test_reject_document(document, user):
    from apps.documents.models import DocumentApproval
    from apps.documents.services import reject_document
    document.status = "revisione"
    document.save(update_fields=["status"])
    reject_document(document, user, notes="manca sezione")
    document.refresh_from_db()
    assert document.status == "bozza"
    assert DocumentApproval.objects.filter(document=document, action="reject").exists()


def test_add_version_increments(document, user):
    from apps.documents.models import DocumentVersion
    from apps.documents.services import add_version
    v1 = add_version(document, "f1.pdf", "abc", "documents/x/v1/f1.pdf", user, "prima", 100)
    v2 = add_version(document, "f2.pdf", "def", "documents/x/v2/f2.pdf", user, "seconda", 200)
    assert v1.version_number == 1 and v2.version_number == 2
    assert DocumentVersion.objects.filter(document=document).count() == 2


def test_get_expiring_documents(plant, user):
    from apps.documents.models import Document
    from apps.documents.services import get_expiring_documents
    today = timezone.localdate()
    soon = Document.objects.create(
        title="In scadenza", category="policy", document_type="policy", status="approvato",
        plant=plant, created_by=user, expiry_date=today + datetime.timedelta(days=10),
    )
    Document.objects.create(
        title="Lontano", category="policy", document_type="policy", status="approvato",
        plant=plant, created_by=user, expiry_date=today + datetime.timedelta(days=200),
    )
    ids = {d.id for d in get_expiring_documents(days=30)}
    assert soon.id in ids


def test_delete_document_blocks_approved_for_non_superuser(document, user):
    from django.core.exceptions import ValidationError
    from apps.documents.services import delete_document
    document.status = "approvato"
    document.save(update_fields=["status"])
    with pytest.raises(ValidationError):
        delete_document(document, user)


def test_delete_document_draft_soft_deletes(document, user):
    from apps.documents.services import delete_document
    delete_document(document, user)
    document.refresh_from_db()
    assert document.deleted_at is not None


def test_delete_approved_document_allowed_for_superuser(document, superuser):
    from apps.documents.services import delete_document
    document.status = "approvato"
    document.save(update_fields=["status"])
    delete_document(document, superuser)
    document.refresh_from_db()
    assert document.deleted_at is not None

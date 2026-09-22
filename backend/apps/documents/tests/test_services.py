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


# ── Promemoria automatici: documenti obbligatori non approvati ───────────────

@pytest.fixture
def mandatory_old_document(db, plant, user):
    """Documento obbligatorio, mai approvato, creato oltre la soglia."""
    from django.utils import timezone
    from apps.documents.models import Document
    from apps.documents.tasks import UNAPPROVED_REMINDER_DAYS

    doc = Document.objects.create(
        title="Policy accessi", category="policy", document_type="policy",
        status="bozza", plant=plant, is_mandatory=True, created_by=user,
    )
    # created_at è auto_now_add: lo si sposta indietro con un update diretto
    Document.objects.filter(pk=doc.pk).update(
        created_at=timezone.now() - timezone.timedelta(days=UNAPPROVED_REMINDER_DAYS + 1)
    )
    doc.refresh_from_db()
    return doc


@pytest.mark.django_db
def test_reminder_created_for_old_mandatory_document(mandatory_old_document, superuser):
    from apps.documents.tasks import remind_unapproved_mandatory_documents
    from apps.tasks.models import Task

    remind_unapproved_mandatory_documents()

    task = Task.objects.get(source_module="M07", source_id=mandatory_old_document.pk)
    assert task.status == "aperto"
    # Assegnato a ruolo, mai a utente (regola #7)
    assert task.assigned_role == "compliance_officer"
    assert task.assigned_to is None


@pytest.mark.django_db
def test_reminder_not_duplicated(mandatory_old_document, superuser):
    from apps.documents.tasks import remind_unapproved_mandatory_documents
    from apps.tasks.models import Task

    remind_unapproved_mandatory_documents()
    remind_unapproved_mandatory_documents()
    remind_unapproved_mandatory_documents()

    assert Task.objects.filter(source_module="M07", source_id=mandatory_old_document.pk).count() == 1


@pytest.mark.django_db
def test_reminder_not_reopened_after_cancel(mandatory_old_document, superuser):
    """Se chi lo riceve lo annulla, il promemoria non ricompare."""
    from apps.documents.tasks import remind_unapproved_mandatory_documents
    from apps.tasks.models import Task

    remind_unapproved_mandatory_documents()
    Task.objects.filter(source_module="M07").update(status="annullato")
    remind_unapproved_mandatory_documents()

    assert Task.objects.filter(source_module="M07", source_id=mandatory_old_document.pk).count() == 1


@pytest.mark.django_db
def test_recent_or_optional_documents_have_no_reminder(document, plant, user, superuser):
    """Né i documenti non obbligatori né quelli creati da poco."""
    from apps.documents.models import Document
    from apps.documents.tasks import remind_unapproved_mandatory_documents
    from apps.tasks.models import Task

    document.is_mandatory = False
    document.save(update_fields=["is_mandatory"])
    Document.objects.create(
        title="Nuova policy", category="policy", document_type="policy",
        status="bozza", plant=plant, is_mandatory=True, created_by=user,
    )

    remind_unapproved_mandatory_documents()
    assert not Task.objects.filter(source_module="M07").exists()


@pytest.mark.django_db
def test_reminder_closed_on_approval(mandatory_old_document, user, superuser):
    from apps.documents.services import approve_document, submit_for_review
    from apps.documents.tasks import remind_unapproved_mandatory_documents
    from apps.tasks.models import Task

    remind_unapproved_mandatory_documents()
    submit_for_review(mandatory_old_document, user)
    approve_document(mandatory_old_document, user, notes="ok")

    task = Task.objects.get(source_module="M07", source_id=mandatory_old_document.pk)
    assert task.status == "completato"


@pytest.mark.django_db
def test_stale_reminder_closed_by_next_run(mandatory_old_document, superuser):
    """Promemoria rimasto aperto su un documento non più in attesa: il giro
    successivo lo chiude (rete di sicurezza)."""
    from apps.documents.tasks import remind_unapproved_mandatory_documents
    from apps.tasks.models import Task

    remind_unapproved_mandatory_documents()
    # approvazione "fuori flusso" (import dati, migrazione): il task resta aperto
    type(mandatory_old_document).objects.filter(pk=mandatory_old_document.pk).update(status="approvato")

    remind_unapproved_mandatory_documents()
    assert Task.objects.get(source_module="M07", source_id=mandatory_old_document.pk).status == "completato"


@pytest.mark.django_db
def test_expiry_reminder_not_duplicated_daily(plant, user, superuser):
    """Il promemoria di scadenza non si ripete ogni giorno sullo stesso documento."""
    from django.utils import timezone
    from apps.documents.models import Document
    from apps.documents.tasks import notify_expiring_documents
    from apps.tasks.models import Task

    Document.objects.create(
        title="Manuale ISMS", category="procedura", document_type="manuale",
        status="approvato", plant=plant, created_by=user,
        review_due_date=timezone.localdate() - timezone.timedelta(days=3),
    )
    notify_expiring_documents()
    first = Task.objects.filter(source_module="M07").count()
    notify_expiring_documents()

    assert first > 0
    assert Task.objects.filter(source_module="M07").count() == first


# ── Numero di revisione del documento (frontespizio) ────────────────────────

@pytest.mark.django_db
def test_version_label_stored_and_displayed(document, user):
    """L'etichetta la scrive chi carica; il contatore interno resta separato."""
    from apps.documents.serializers import DocumentVersionSerializer
    from apps.documents.services import add_version

    v1 = add_version(document, "f1.pdf", "abc", "p/v1.pdf", user, "prima", 100,
                     version_label="Rev. 03")
    v2 = add_version(document, "f2.pdf", "def", "p/v2.pdf", user, "seconda", 100)

    assert (v1.version_number, v1.version_label) == (1, "Rev. 03")
    assert (v2.version_number, v2.version_label) == (2, "")
    # senza etichetta la UI mostra il contatore
    assert DocumentVersionSerializer(v1).data["version_display"] == "Rev. 03"
    assert DocumentVersionSerializer(v2).data["version_display"] == "v2"


@pytest.mark.django_db
def test_upload_endpoint_accepts_version_label(document, user):
    from django.core.files.uploadedfile import SimpleUploadedFile
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    from rest_framework.test import APIClient

    UserPlantAccess.objects.create(user=user, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    client = APIClient()
    client.force_authenticate(user=user)

    resp = client.post(
        f"/api/v1/documents/documents/{document.id}/upload/",
        {"file": SimpleUploadedFile("policy.pdf", b"%PDF-1.4 contenuto", content_type="application/pdf"),
         "version_label": "2.1", "change_summary": "revisione annuale"},
        format="multipart",
    )
    assert resp.status_code == 201, resp.data
    assert resp.data["version_label"] == "2.1"
    assert resp.data["version_display"] == "2.1"

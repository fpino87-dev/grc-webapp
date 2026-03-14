import datetime

from django.utils import timezone

from core.audit import log_action

from .models import Document, DocumentApproval, DocumentVersion


def submit_for_review(document, user):
    document.status = "revisione"
    document.save(update_fields=["status", "updated_at"])
    log_action(
        user=user,
        action_code="document.submitted_for_review",
        level="L2",
        entity=document,
        payload={"id": str(document.pk), "title": document.title},
    )


def approve_document(document, user, notes=""):
    document.status = "approvato"
    document.approved_at = timezone.now()
    document.approver = user
    document.save(update_fields=["status", "approved_at", "approver", "updated_at"])
    DocumentApproval.objects.create(
        document=document, action="approve", actor=user, notes=notes
    )
    log_action(
        user=user,
        action_code="document.approved",
        level="L2",
        entity=document,
        payload={"id": str(document.pk), "title": document.title, "notes": notes},
    )


def reject_document(document, user, notes=""):
    document.status = "bozza"
    document.save(update_fields=["status", "updated_at"])
    DocumentApproval.objects.create(
        document=document, action="reject", actor=user, notes=notes
    )
    log_action(
        user=user,
        action_code="document.rejected",
        level="L2",
        entity=document,
        payload={"id": str(document.pk), "title": document.title, "notes": notes},
    )


def add_version(
    document, file_name, sha256, storage_path, user, change_summary="", file_size=None
):
    last = document.versions.first()
    version_number = (last.version_number + 1) if last else 1
    v = DocumentVersion.objects.create(
        document=document,
        version_number=version_number,
        file_name=file_name,
        sha256=sha256,
        storage_path=storage_path,
        change_summary=change_summary,
        file_size=file_size,
        uploaded_by=user,
    )
    log_action(
        user=user,
        action_code=f"document.version_added",
        level="L1",
        entity=document,
        payload={
            "id": str(document.pk),
            "version_number": version_number,
            "file_name": file_name,
        },
    )
    return v


def get_expiring_documents(days=30):
    cutoff = timezone.now().date() + datetime.timedelta(days=days)
    return (
        Document.objects.filter(status="approvato", expiry_date__lte=cutoff)
        .select_related("plant", "owner")
    )

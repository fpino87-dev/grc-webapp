import datetime
import hashlib
import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.utils import timezone

from django.utils.translation import gettext as _

from core.audit import log_action
from core.uploads import (
    DEFAULT_MAX_FILE_SIZE_BYTES as MAX_FILE_SIZE_BYTES,
    OFFICE_EXTENSIONS as ALLOWED_EXTENSIONS,
    OFFICE_MIME_TYPES as ALLOWED_MIME_TYPES,
    validate_uploaded_file,
)

from .models import Document, DocumentApproval, DocumentVersion, Evidence


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
    # Notifica ruoli di revisione definiti in governance
    try:
        from apps.governance.services import resolve_document_recipients
        from apps.notifications.services import notify_document_review_needed

        recipients = resolve_document_recipients(document, action="review")
        if recipients:
            notify_document_review_needed(document, recipients)
    except Exception:
        # Le notifiche non devono bloccare il flusso documentale
        pass


def approve_document(document, user, notes=""):
    document.status = "approvato"
    document.approved_at = timezone.now()
    document.approver = user
    # Set review_due_date from configurable schedule policy
    try:
        from apps.compliance_schedule.services import get_due_date
        plant = getattr(document, "plant", None)
        rule_type = f"document_{document.document_type}"
        document.review_due_date = get_due_date(rule_type, plant=plant)
    except Exception:
        pass
    document.save(update_fields=["status", "approved_at", "approver", "review_due_date", "updated_at"])
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
    # notifica approvatori / stakeholder definiti in governance
    try:
        from apps.governance.services import resolve_document_recipients
        from apps.notifications.services import (
            notify_document_approval_needed,
            notify_document_approved_broadcast,
        )
        from apps.auth_grc.services import resolve_plant_member_emails

        # 1) Notifica a ruoli di approvazione (es. Plant Manager, CISO)
        approval_recipients = resolve_document_recipients(document, action="approve")
        if approval_recipients:
            notify_document_approval_needed(document, approval_recipients)

        # 2) Broadcast a tutti i membri del sito
        if document.plant:
            members = resolve_plant_member_emails(document.plant)
            if members:
                notify_document_approved_broadcast(document, members)
    except Exception:
        # Le notifiche non devono bloccare il flusso documentale
        pass


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
    """
    Mantiene compatibilità con eventuali chiamate esistenti.
    Preferire add_version_with_file per i nuovi flussi con upload reale.
    """
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
        action_code="document.version_added",
        level="L1",
        entity=document,
        payload={
            "id": str(document.pk),
            "version_number": version_number,
            "file_name": file_name,
        },
    )
    return v


def add_version_with_file(document, uploaded_file, user, change_summary=""):
    validate_uploaded_file(uploaded_file)

    content = uploaded_file.read()
    sha256_hash = hashlib.sha256(content).hexdigest()
    file_size = len(content)

    last = document.versions.first()
    version_number = (last.version_number + 1) if last else 1

    original_name = getattr(uploaded_file, "name", "document")
    relative_path = os.path.join(
        "documents",
        str(document.id),
        f"v{version_number}",
        original_name,
    )

    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    storage_path = default_storage.save(relative_path, uploaded_file)

    if last and last.storage_path:
        try:
            default_storage.delete(last.storage_path)
        except Exception:
            # In caso di errore nella cancellazione fisica non blocchiamo il flusso
            pass

    version = DocumentVersion.objects.create(
        document=document,
        version_number=version_number,
        file_name=original_name,
        file_size=file_size,
        sha256=sha256_hash,
        storage_path=storage_path,
        change_summary=change_summary,
        uploaded_by=user,
    )

    log_action(
        user=user,
        action_code="document.version_added",
        level="L1",
        entity=document,
        payload={
            "id": str(document.pk),
            "version_number": version_number,
            "file_name": original_name,
        },
    )
    return version


def get_expiring_documents(days=30):
    cutoff = timezone.now().date() + datetime.timedelta(days=days)
    return (
        Document.objects.filter(status="approvato", expiry_date__lte=cutoff)
        .select_related("plant", "owner")
    )


def create_evidence_with_file(data, uploaded_file, user):
    """
    Crea una Evidence con upload file gestito via default_storage.
    """
    from django.utils.dateparse import parse_date

    validate_uploaded_file(uploaded_file)

    title = data.get("title", "")
    evidence_type = data.get("evidence_type") or "altro"
    description = data.get("description", "")
    valid_until_raw = data.get("valid_until")
    valid_until = parse_date(valid_until_raw) if valid_until_raw else None
    plant_id = data.get("plant")

    plant = None
    if plant_id:
        from apps.plants.models import Plant

        plant = Plant.objects.filter(pk=plant_id).first()

    evidence = Evidence.objects.create(
        title=title,
        description=description,
        evidence_type=evidence_type,
        valid_until=valid_until,
        plant=plant,
        uploaded_by=user,
        created_by=user,
    )

    original_name = getattr(uploaded_file, "name", "evidence")
    relative_path = os.path.join("evidences", str(evidence.id), original_name)
    storage_path = default_storage.save(relative_path, uploaded_file)

    evidence.file_path = storage_path
    evidence.save(update_fields=["file_path", "updated_at"])

    log_action(
        user=user,
        action_code="evidence.created_with_file",
        level="L2",
        entity=evidence,
        payload={
            "id": str(evidence.pk),
            "title": evidence.title,
            "file_path": storage_path,
        },
    )

    return evidence


def delete_document(document, user) -> None:
    """
    Soft delete di un documento M07. Rimuove i collegamenti ai controlli.
    Documenti approvati: solo superuser.
    """
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    if document.status in ("approvazione", "approvato") and not user.is_superuser:
        raise ValidationError(
            _("Eliminazione non consentita per documenti in approvazione o già approvati.")
        )

    document.control_refs.clear()
    document.soft_delete()

    log_action(
        user=user,
        action_code="document.deleted",
        level="L2",
        entity=document,
        payload={"id": str(document.pk), "title": document.title, "status": document.status},
    )


def delete_evidence(evidence, user) -> None:
    """Soft delete evidenza e rimozione collegamenti ai ControlInstance."""
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    from apps.controls.models import ControlInstance

    linked = ControlInstance.objects.filter(evidences=evidence, deleted_at__isnull=True).exclude(
        status="non_valutato"
    )
    if linked.exists() and not user.is_superuser:
        raise ValidationError(
            _("Eliminazione non consentita: l'evidenza è collegata a controlli già valutati.")
        )

    evidence.control_instances.clear()
    evidence.soft_delete()

    log_action(
        user=user,
        action_code="evidence.deleted",
        level="L2",
        entity=evidence,
        payload={"id": str(evidence.pk), "title": evidence.title},
    )

import datetime
import hashlib
import logging
import os

from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _lazy

from core.audit import log_action
from core.uploads import (
    validate_uploaded_file,
)

from .models import Document, DocumentApproval, DocumentVersion, Evidence

# ── Macchina a stati del workflow documentale (M07) ─────────────────────────
# Le transizioni di stato passano SOLO da qui: il serializer espone `status`,
# `approver` e `approved_at` in sola lettura, così un'approvazione non può
# avvenire senza controllo di policy, record DocumentApproval e audit trail
# (ISO/IEC 27001 §7.5.2 — approvazione dell'informazione documentata).
# Stati in cui il documento non è (ancora) in vigore: usati dal promemoria
# automatico M07 e dallo snapshot del riesame di direzione.
PENDING_STATUSES = ("bozza", "revisione", "approvazione")

# Promemoria automatici sui documenti (task M08 con sorgente M07).
REMINDER_SOURCE_MODULE = "M07"
OPEN_TASK_STATUSES = ("aperto", "in_corso")
# Un promemoria già annullato da chi l'ha ricevuto non viene riaperto.
BLOCKING_TASK_STATUSES = OPEN_TASK_STATUSES + ("annullato",)

ALLOWED_TRANSITIONS = {
    # invio in revisione: da bozza, o da approvato per la revisione periodica
    "submit": {"bozza", "approvato"},
    # approvazione/rifiuto: solo su un documento effettivamente in lavorazione
    "approve": {"revisione", "approvazione"},
    "reject": {"revisione", "approvazione"},
    # archiviazione: solo un documento che è stato in vigore
    "archive": {"approvato"},
    # delibera dell'organo di governo: è l'atto che manda in vigore il
    # documento, anche se l'iter interno non era stato avviato. Il vincolo
    # bozza → approvato esiste per impedire l'approvazione silenziosa di un
    # singolo utente, non per limitare il CdA — e resta tracciato che si è
    # trattato di una delibera, con i suoi estremi.
    "approve_resolution": {"bozza", "revisione", "approvazione"},
}

_TRANSITION_ERRORS = {
    "submit": _lazy("Invio in revisione non consentito da questo stato: %(status)s."),
    "approve_resolution": _lazy(
        "Delibera non registrabile: il documento è già in vigore o archiviato "
        "(stato attuale: %(status)s)."
    ),
    "approve": _lazy("Approvazione non consentita: il documento non è in revisione o in approvazione (stato attuale: %(status)s)."),
    "reject": _lazy("Rifiuto non consentito: il documento non è in revisione o in approvazione (stato attuale: %(status)s)."),
    "archive": _lazy("Archiviazione non consentita: solo un documento approvato può essere archiviato (stato attuale: %(status)s)."),
}


def _require_transition(document, action: str) -> None:
    """Blocca i salti di stato (es. bozza → approvato) prima di ogni scrittura."""
    allowed = ALLOWED_TRANSITIONS.get(action, set())
    if document.status not in allowed:
        raise ValidationError(
            _TRANSITION_ERRORS[action] % {"status": document.get_status_display()}
        )


def submit_for_review(document, user):
    _require_transition(document, "submit")
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
    except Exception as exc:
        # Le notifiche non devono bloccare il flusso documentale
        logging.getLogger(__name__).warning("Documenti: notifica non inviata: %s", exc)


def can_register_resolution(user) -> bool:
    """Chi può registrare una delibera dell'organo su un documento.

    Non è chi *approva* (quello lo dice la policy di workflow con i ruoli
    normativi): la delibera l'ha assunta l'organo in seduta, qui la si
    trascrive. Vale quindi lo stesso criterio del riesame di direzione —
    la registra governance, con il verbale firmato come evidenza.
    """
    from apps.auth_grc.models import GrcRole
    from core.permissions import user_has_any_role

    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return user_has_any_role(user, {GrcRole.SUPER_ADMIN, GrcRole.COMPLIANCE_OFFICER})


def _approval_timestamp(resolution_date):
    """Istante di entrata in vigore: mezzogiorno del giorno di delibera (così
    nessun fuso sposta il documento al giorno prima o dopo), altrimenti adesso."""
    if resolution_date is None:
        return timezone.now()
    return timezone.make_aware(
        datetime.datetime.combine(resolution_date, datetime.time(12, 0)),
        timezone.get_current_timezone(),
    )


def _document_authors(document) -> set:
    """Chi ha redatto il documento: chi l'ha creato e chi ha caricato la
    versione attualmente in esame."""
    authors = {document.created_by_id}
    latest = document.versions.first()
    if latest is not None:
        authors.add(latest.uploaded_by_id)
    return {a for a in authors if a}


def _require_author_separation(document, user, action: str) -> None:
    """Segregazione dei compiti sulla revisione (ISO/IEC 27001 §5.3).

    Vale dove la policy di workflow la richiede: su quei tipi di documento chi
    ha scritto il testo non può essere anche chi ne chiude la revisione. Non ha
    eccezioni per i superuser: è una regola di processo, non un permesso — se
    serve derogare si cambia la policy, e resta scritto in Governance.
    """
    from apps.governance.services import resolve_document_workflow_policy

    policy = resolve_document_workflow_policy(
        getattr(document, "document_type", None) or "altro", getattr(document, "plant", None),
    )
    if policy is None or not policy.require_distinct_reviewer:
        return
    if user.pk not in _document_authors(document):
        return

    if action == "approve":
        raise ValidationError(
            _("Chi ha redatto il documento non può approvarlo: la revisione spetta "
              "a un'altra persona fra quelle previste dal workflow documentale.")
        )
    raise ValidationError(
        _("Chi ha redatto il documento non può respingerlo: la revisione spetta "
          "a un'altra persona fra quelle previste dal workflow documentale.")
    )


def _validate_approval_mode(document, mode, resolution_ref, resolution_date, governing_body,
                            from_review=False):
    """Controlla la modalità di approvazione rispetto alla policy di workflow.

    Un tipo di documento che la governance riserva all'organo (politiche
    deliberate dal CdA) non si approva in applicazione: serve la delibera.
    """
    from apps.governance.services import resolve_document_workflow_policy

    if mode not in ("in_app", "delibera"):
        raise ValidationError(_("Modalità di approvazione non valida."))

    policy = resolve_document_workflow_policy(
        getattr(document, "document_type", None) or "altro", getattr(document, "plant", None),
    )
    if mode == "in_app":
        if policy is not None and policy.requires_body_resolution:
            raise ValidationError(
                _("Documenti di questo tipo entrano in vigore solo con delibera "
                  "dell'organo di governo: registra gli estremi della delibera.")
            )
        return mode, None, None

    if isinstance(resolution_date, str) and resolution_date:
        try:
            resolution_date = datetime.date.fromisoformat(resolution_date)
        except ValueError:
            raise ValidationError(
                _("Data della delibera non valida (formato atteso: AAAA-MM-GG).")
            ) from None
    if not resolution_date:
        raise ValidationError(_("Indicare la data della decisione dell'organo."))
    # Il numero di delibera serve quando la decisione è presa fuori dalla
    # piattaforma: se arriva da un riesame di direzione, il riferimento è la
    # seduta stessa, già collegata al documento.
    if not from_review and not (resolution_ref or "").strip():
        raise ValidationError(_("Indicare numero e data della delibera."))
    if resolution_date > timezone.localdate():
        raise ValidationError(_("La data della delibera non può essere futura."))

    if governing_body is None and policy is not None:
        governing_body = policy.approval_body
    return mode, resolution_date, governing_body


def approve_document(
    document,
    user,
    notes="",
    *,
    mode="in_app",
    resolution_ref="",
    resolution_date=None,
    governing_body=None,
    review_id=None,
):
    """Manda in vigore il documento.

    ``mode="in_app"``: approva chi preme il pulsante, con il ruolo previsto
    dalla policy di workflow. ``mode="delibera"``: l'organo di governo ha
    deliberato in seduta e qui se ne registrano gli estremi; la data di
    approvazione è quella della delibera, non quella della registrazione (che
    resta nel record e nell'audit trail).
    """
    mode, resolution_date, governing_body = _validate_approval_mode(
        document, mode, resolution_ref, resolution_date, governing_body,
        from_review=bool(review_id),
    )
    if mode == "in_app":
        _require_author_separation(document, user, "approve")
    _require_transition(document, "approve_resolution" if mode == "delibera" else "approve")
    document.status = "approvato"
    document.approved_at = _approval_timestamp(resolution_date)
    document.approver = user
    # Set review_due_date from configurable schedule policy
    try:
        from apps.compliance_schedule.services import get_due_date
        plant = getattr(document, "plant", None)
        rule_type = f"document_{document.document_type}"
        document.review_due_date = get_due_date(rule_type, plant=plant)
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "Documento %s: scadenza revisione non calcolata: %s", document.pk, exc,
        )
    # Atomica (P1-2): stato documento + record approvazione + audit append-only
    # vanno insieme; le notifiche restano fuori dalla transazione (best-effort, I/O).
    # La versione in vigore è l'ultima caricata al momento dell'approvazione.
    approved = document.versions.first()

    with transaction.atomic():
        document.save(update_fields=["status", "approved_at", "approver", "review_due_date", "updated_at"])
        DocumentApproval.objects.create(
            document=document, action="approve", actor=user, notes=notes,
            version=approved,
            approval_mode=mode,
            governing_body=governing_body,
            resolution_ref=(resolution_ref or "").strip()[:100] if mode == "delibera" else "",
            resolution_date=resolution_date if mode == "delibera" else None,
            review_id=review_id if mode == "delibera" else None,
        )
        log_action(
            user=user,
            action_code="document.approved",
            level="L2",
            entity=document,
            payload={
                "id": str(document.pk), "title": document.title,
                "notes": (notes or "")[:200], "mode": mode,
                "resolution_ref": (resolution_ref or "")[:100] if mode == "delibera" else "",
                "resolution_date": str(resolution_date) if resolution_date else None,
                "version": (approved.version_label or f"v{approved.version_number}") if approved else None,
            },
        )
    # Il documento è in vigore: i promemoria automatici aperti su di esso non
    # servono più (stesso schema dei promemoria del piano formativo, M15).
    close_document_reminders(document, user, _("Documento approvato."))

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
    except Exception as exc:
        # Le notifiche non devono bloccare il flusso documentale
        logging.getLogger(__name__).warning("Documenti: notifica non inviata: %s", exc)


def reject_document(document, user, notes=""):
    _require_author_separation(document, user, "reject")
    _require_transition(document, "reject")
    with transaction.atomic():
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
            payload={"id": str(document.pk), "title": document.title, "notes": (notes or "")[:200]},
        )


def archive_document(document, user, notes=""):
    """Manda fuori vigore un documento approvato (nessuna eliminazione: lo
    storico resta consultabile per l'audit)."""
    _require_transition(document, "archive")
    with transaction.atomic():
        document.status = "archiviato"
        document.save(update_fields=["status", "updated_at"])
        log_action(
            user=user,
            action_code="document.archived",
            level="L2",
            entity=document,
            payload={"id": str(document.pk), "title": document.title, "notes": (notes or "")[:200]},
        )


def close_document_reminders(document, user, notes="") -> int:
    """Chiude i promemoria automatici (M08) aperti su un documento.

    Best-effort: un errore qui non deve far fallire l'approvazione. I task
    rimasti aperti per un documento ormai approvato vengono comunque chiusi dal
    giro successivo di `remind_unapproved_mandatory_documents`.
    """
    from apps.tasks.models import Task
    from apps.tasks.services import complete_task

    closed = 0
    try:
        for task in Task.objects.filter(
            source_module=REMINDER_SOURCE_MODULE,
            source_id=document.pk,
            status__in=OPEN_TASK_STATUSES,
        ):
            complete_task(task, user, notes=notes)
            closed += 1
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "Documento %s: chiusura promemoria non riuscita: %s", document.pk, exc,
        )
    return closed


def add_version(
    document, file_name, sha256, storage_path, user, change_summary="", file_size=None,
    version_label="",
):
    """
    Mantiene compatibilità con eventuali chiamate esistenti.
    Preferire add_version_with_file per i nuovi flussi con upload reale.
    """
    last = document.versions.first()
    version_number = (last.version_number + 1) if last else 1
    with transaction.atomic():
        v = DocumentVersion.objects.create(
            document=document,
            version_number=version_number,
            version_label=(version_label or "").strip()[:50],
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


def approved_version(document):
    """Versione attualmente approvata, se l'approvazione la registra."""
    record = (
        document.approvals.filter(action="approve", version__isnull=False)
        .order_by("-created_at").first()
    )
    return record.version if record else None


def has_unapproved_version(document) -> bool:
    """True se dopo l'ultima approvazione è stata caricata una nuova versione.

    Vale solo per i documenti che risultano in vigore: per gli altri lo stato
    dice già che non sono approvati. Sulle approvazioni registrate prima del
    collegamento versione-approvazione non si segnala nulla, perché non si sa
    quale versione fosse stata approvata.
    """
    if document.status != "approvato":
        return False
    latest = document.versions.first()
    if latest is None:
        return False
    current = approved_version(document)
    return current is not None and current.pk != latest.pk


def _reopen_for_new_version(document, user, version):
    """Nuova versione su un documento in vigore.

    Per i documenti obbligatori il testo cambiato non resta in vigore senza una
    nuova approvazione: il documento torna in revisione (§7.5.3, controllo delle
    modifiche). Per gli altri lo stato non cambia e la nuova versione resta
    segnalata come non ancora approvata.
    """
    if document.status != "approvato" or not document.is_mandatory:
        return

    document.status = "revisione"
    document.save(update_fields=["status", "updated_at"])
    log_action(
        user=user,
        action_code="document.reopened_by_new_version",
        level="L2",
        entity=document,
        payload={
            "id": str(document.pk),
            "title": document.title,
            "version": version.version_label or f"v{version.version_number}",
        },
    )
    try:
        from apps.governance.services import resolve_document_recipients
        from apps.notifications.services import notify_document_review_needed

        recipients = resolve_document_recipients(document, action="review")
        if recipients:
            notify_document_review_needed(document, recipients)
    except Exception as exc:
        logging.getLogger(__name__).warning("Documenti: notifica non inviata: %s", exc)


def add_version_with_file(document, uploaded_file, user, change_summary="", version_label=""):
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

    # La rimozione del file della versione precedente è schedulata DOPO il commit
    # (transaction.on_commit): se la scrittura DB sotto fa rollback, il file vecchio
    # resta integro (la riga superstite continuerebbe a puntarci). Best-effort.
    old_path = last.storage_path if (last and last.storage_path) else None

    # Atomica (P1-2) solo sulle scritture DB (create versione + audit). Lo storage
    # del nuovo file è già avvenuto sopra e resta fuori dalla transazione (I/O su FS).
    with transaction.atomic():
        version = DocumentVersion.objects.create(
            document=document,
            version_number=version_number,
            version_label=(version_label or "").strip()[:50],
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
                "version_label": version.version_label,
                "file_name": original_name,
            },
        )

    _reopen_for_new_version(document, user, version)

    if old_path:
        def _delete_old():
            try:
                default_storage.delete(old_path)
            except Exception as exc:
                logging.getLogger(__name__).warning(
                    "Documento %s: rimozione file versione precedente fallita "
                    "(possibile file orfano in storage): %s",
                    document.pk, exc,
                )
        transaction.on_commit(_delete_old)
    return version


def get_expiring_documents(days=30):
    """Documenti approvati in scadenza entro `days` giorni dall'"oggi" del sito
    (F3, timezone per Plant); per i documenti senza sito vale l'orologio server."""
    from django.db.models import Q

    from apps.plants.services import per_plant_today_q

    server_cutoff = timezone.localdate() + datetime.timedelta(days=days)
    cond = per_plant_today_q(
        lambda today, ids: Q(
            plant_id__in=ids, expiry_date__lte=today + datetime.timedelta(days=days)
        )
    ) | Q(plant__isnull=True, expiry_date__lte=server_cutoff)
    return (
        Document.objects.filter(status="approvato")
        .filter(cond)
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

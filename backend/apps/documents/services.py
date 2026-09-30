import datetime
import hashlib
import logging
import os

from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _lazy

from core.audit import log_action
from core.uploads import (
    validate_uploaded_file,
)

from . import pdf_converter
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
    # respingimento deciso dall'organo (riesame mirato): da bozza il documento
    # resta in bozza e si registra solo l'esito sulla revisione esaminata.
    "reject_resolution": {"bozza", "revisione", "approvazione"},
}

_TRANSITION_ERRORS = {
    "submit": _lazy("Invio in revisione non consentito da questo stato: %(status)s."),
    "approve_resolution": _lazy(
        "Delibera non registrabile: il documento è già in vigore o archiviato "
        "(stato attuale: %(status)s)."
    ),
    "approve": _lazy("Approvazione non consentita: il documento non è in revisione o in approvazione (stato attuale: %(status)s)."),
    "reject": _lazy("Rifiuto non consentito: il documento non è in revisione o in approvazione (stato attuale: %(status)s)."),
    "reject_resolution": _lazy(
        "Respingimento non registrabile: il documento è in vigore senza nuove versioni o è "
        "archiviato (stato attuale: %(status)s)."
    ),
    "archive": _lazy("Archiviazione non consentita: solo un documento approvato può essere archiviato (stato attuale: %(status)s)."),
}


def _require_transition(document, action: str) -> None:
    """Blocca i salti di stato (es. bozza → approvato) prima di ogni scrittura."""
    allowed = ALLOWED_TRANSITIONS.get(action, set())
    # L'organo decide anche su una nuova versione caricata dopo l'ultima
    # approvazione di un documento che resta in vigore (non obbligatorio).
    if action in ("approve_resolution", "reject_resolution") and has_unapproved_version(document):
        return
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
    # Le versioni superate da questa approvazione non servono più in storage.
    transaction.on_commit(lambda: prune_superseded_files(document))

    # Il documento è in vigore: i promemoria automatici aperti su di esso non
    # servono più (stesso schema dei promemoria del piano formativo, M15).
    close_document_reminders(document, user, _("Documento approvato."))

    # I controlli scesi a Parziale mentre il documento era in revisione tornano
    # Compliant. Best-effort: se fallisce ci ripensa il task notturno.
    try:
        from apps.controls.services import restore_controls_for_document

        with transaction.atomic():
            restore_controls_for_document(document, user)
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "Documento %s: ripristino controlli collegati non riuscito: %s", document.pk, exc,
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
    except Exception as exc:
        # Le notifiche non devono bloccare il flusso documentale
        logging.getLogger(__name__).warning("Documenti: notifica non inviata: %s", exc)


def reject_document(
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
    """Respinge la revisione in esame: il documento torna in bozza.

    ``mode="delibera"``: lo ha deciso l'organo di governo in seduta (riesame
    mirato). È un atto collegiale come l'approvazione per delibera: niente
    controllo di separazione autore-revisore; da bozza il documento resta in
    bozza, e un documento in vigore con una nuova versione resta in vigore con
    la versione già approvata. In entrambi i casi si registra quale revisione
    è stata respinta.
    """
    if mode == "delibera":
        mode, resolution_date, governing_body = _validate_approval_mode(
            document, mode, resolution_ref, resolution_date, governing_body,
            from_review=bool(review_id),
        )
        _require_transition(document, "reject_resolution")
    else:
        mode = "in_app"
        _require_author_separation(document, user, "reject")
        _require_transition(document, "reject")
    new_status = "bozza" if document.status in ("revisione", "approvazione") else document.status
    rejected = document.versions.first()
    with transaction.atomic():
        if new_status != document.status:
            document.status = new_status
            document.save(update_fields=["status", "updated_at"])
        DocumentApproval.objects.create(
            document=document, action="reject", actor=user, notes=notes,
            version=rejected,
            approval_mode=mode,
            governing_body=governing_body if mode == "delibera" else None,
            resolution_ref=(resolution_ref or "").strip()[:100] if mode == "delibera" else "",
            resolution_date=resolution_date if mode == "delibera" else None,
            review_id=review_id if mode == "delibera" else None,
        )
        log_action(
            user=user,
            action_code="document.rejected",
            level="L2",
            entity=document,
            payload={
                "id": str(document.pk), "title": document.title,
                "notes": (notes or "")[:200], "mode": mode,
                "resolution_ref": (resolution_ref or "")[:100] if mode == "delibera" else "",
                "version": (rejected.version_label or f"v{rejected.version_number}") if rejected else None,
            },
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
            pdf_status=(
                DocumentVersion.PDF_PENDING
                if pdf_converter.is_convertible(original_name)
                else DocumentVersion.PDF_NOT_APPLICABLE
            ),
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

    # Dopo il commit: il file della versione precedente se ne va solo se non è
    # quella in vigore, e la copia PDF si genera in background.
    transaction.on_commit(lambda: prune_superseded_files(document))
    if version.pdf_status == DocumentVersion.PDF_PENDING:
        schedule_version_pdf(version)
    return version


# ── File conservati e copia PDF ─────────────────────────────────────────────
# Per ogni documento restano nello storage solo i file dell'ultima versione
# caricata e della versione approvata (in vigore): è quest'ultima che va
# all'auditor anche mentre una nuova bozza è in revisione. Delle versioni
# superate resta la riga (numero, autore, hash), non il file.

def prune_superseded_files(document) -> int:
    """Elimina i file delle versioni né ultime né in vigore. Best-effort."""
    versions = list(document.versions.all())
    if not versions:
        return 0
    keep = {versions[0].pk}
    current = approved_version(document)
    if current is not None:
        keep.add(current.pk)
    pruned = 0
    for v in versions[1:]:
        if v.pk in keep or not (v.storage_path or v.pdf_storage_path):
            continue
        for path in (v.storage_path, v.pdf_storage_path):
            if not path:
                continue
            try:
                default_storage.delete(path)
            except Exception as exc:
                logging.getLogger(__name__).warning(
                    "Documento %s: rimozione file della versione %s fallita "
                    "(possibile file orfano in storage): %s",
                    document.pk, v.version_number, exc,
                )
        v.storage_path = ""
        v.pdf_storage_path = ""
        if v.pdf_status in (DocumentVersion.PDF_PENDING, DocumentVersion.PDF_READY):
            v.pdf_status = DocumentVersion.PDF_NOT_APPLICABLE
        v.save(update_fields=["storage_path", "pdf_storage_path", "pdf_status", "updated_at"])
        pruned += 1
    return pruned


def schedule_version_pdf(version) -> None:
    """Accoda la generazione del PDF dopo il commit della transazione."""
    from .tasks import generate_version_pdf_task

    version_id = str(version.pk)
    transaction.on_commit(lambda: generate_version_pdf_task.delay(version_id))


def _pdf_audit_user(version):
    if version.uploaded_by_id:
        return version.uploaded_by
    from django.contrib.auth import get_user_model

    return get_user_model().objects.filter(is_superuser=True).first()


def generate_version_pdf(version) -> str:
    """Genera (o rigenera) la copia PDF di una versione Word.

    Esiti: ``ok``; ``pending`` se il servizio non è raggiungibile (si riprova
    col passaggio notturno); ``failed`` se il file non è convertibile; ``na``
    se non c'è niente da convertire (formato non Word o file non più in
    storage). Restituisce lo stato finale.
    """
    log = logging.getLogger(__name__)
    if not version.storage_path or not pdf_converter.is_convertible(version.file_name):
        _set_pdf_status(version, DocumentVersion.PDF_NOT_APPLICABLE)
        return version.pdf_status
    if not default_storage.exists(version.storage_path):
        _set_pdf_status(version, DocumentVersion.PDF_NOT_APPLICABLE)
        return version.pdf_status

    with default_storage.open(version.storage_path, "rb") as fh:
        content = fh.read()
    try:
        pdf_bytes = pdf_converter.convert_to_pdf(version.file_name, content)
    except pdf_converter.ConversionUnavailable as exc:
        log.warning("PDF versione %s rimandato: servizio non disponibile (%s)", version.pk, exc)
        _set_pdf_status(version, DocumentVersion.PDF_PENDING)
        return version.pdf_status
    except pdf_converter.ConversionFailed as exc:
        log.warning("PDF versione %s non generato: %s", version.pk, exc)
        _set_pdf_status(version, DocumentVersion.PDF_FAILED)
        _log_pdf_outcome(version, "document.pdf_failed", {"reason": str(exc)[:200]})
        return version.pdf_status

    from django.core.files.base import ContentFile

    stem = os.path.splitext(os.path.basename(version.file_name))[0] or "documento"
    relative_path = os.path.join(
        "documents", str(version.document_id), f"v{version.version_number}", "pdf", f"{stem}.pdf",
    )
    old_pdf = version.pdf_storage_path
    version.pdf_storage_path = default_storage.save(relative_path, ContentFile(pdf_bytes))
    version.pdf_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    version.pdf_generated_at = timezone.now()
    version.pdf_status = DocumentVersion.PDF_READY
    version.save(update_fields=[
        "pdf_storage_path", "pdf_sha256", "pdf_generated_at", "pdf_status", "updated_at",
    ])
    if old_pdf and old_pdf != version.pdf_storage_path:
        try:
            default_storage.delete(old_pdf)
        except Exception as exc:
            log.warning("PDF versione %s: vecchia copia non rimossa: %s", version.pk, exc)
    _log_pdf_outcome(version, "document.pdf_generated", {"pdf_sha256": version.pdf_sha256})
    return version.pdf_status


def generate_pending_pdfs(include_failed=False, limit=None) -> dict:
    """Converte le versioni "da generare" (e, a richiesta, quelle fallite).

    Si ferma al primo servizio non disponibile: inutile insistere, le versioni
    restano in coda per il passaggio successivo.
    """
    statuses = [DocumentVersion.PDF_PENDING]
    if include_failed:
        statuses.append(DocumentVersion.PDF_FAILED)
    qs = (
        DocumentVersion.objects.filter(pdf_status__in=statuses, document__deleted_at__isnull=True)
        .select_related("document", "uploaded_by")
        .order_by("created_at")
    )
    if limit:
        qs = qs[:limit]
    counts = {"ok": 0, "failed": 0, "na": 0, "pending": 0}
    if not pdf_converter.is_enabled():
        counts["pending"] = qs.count()
        return counts
    for version in qs:
        status = generate_version_pdf(version)
        counts[status] = counts.get(status, 0) + 1
        if status == DocumentVersion.PDF_PENDING:
            break
    return counts


def _set_pdf_status(version, status) -> None:
    if version.pdf_status != status:
        version.pdf_status = status
        version.save(update_fields=["pdf_status", "updated_at"])


def _log_pdf_outcome(version, action_code, extra) -> None:
    user = _pdf_audit_user(version)
    if user is None:
        return
    log_action(
        user=user,
        action_code=action_code,
        level="L1",
        entity=version.document,
        payload={
            "id": str(version.document_id),
            "version": version.version_label or f"v{version.version_number}",
            "sha256": version.sha256,
            **extra,
        },
    )


def export_file(document):
    """Il file del documento da consegnare all'esterno (pacchetti audit).

    Versione: quella in vigore se l'approvazione la registra, altrimenti
    l'ultima caricata (documenti mai approvati o approvazioni storiche senza
    collegamento alla versione). Formato: la copia PDF se disponibile,
    altrimenti il file originale.

    Restituisce ``None`` se non c'è un file in storage, altrimenti un dict con
    ``version``, ``storage_path``, ``extension``, ``sha256``, ``is_pdf_copy``,
    ``pdf_missing`` (Word senza copia PDF: va segnalato a chi prepara l'audit)
    e ``is_approved_version``.
    """
    candidates = []
    current = approved_version(document)
    if current is not None and current.deleted_at is None:
        candidates.append(current)
    latest = document.versions.first()
    if latest is not None and latest not in candidates:
        candidates.append(latest)

    for version in candidates:
        if version.pdf_status == DocumentVersion.PDF_READY and version.pdf_storage_path \
                and default_storage.exists(version.pdf_storage_path):
            return {
                "version": version,
                "storage_path": version.pdf_storage_path,
                "extension": ".pdf",
                "sha256": version.pdf_sha256,
                "is_pdf_copy": True,
                "pdf_missing": False,
                "is_approved_version": version is current,
            }
        if version.storage_path and default_storage.exists(version.storage_path):
            _, ext = os.path.splitext(version.file_name or version.storage_path)
            return {
                "version": version,
                "storage_path": version.storage_path,
                "extension": ext,
                "sha256": version.sha256,
                "is_pdf_copy": False,
                "pdf_missing": pdf_converter.is_convertible(version.file_name),
                "is_approved_version": version is current,
            }
    return None


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


# ---------------------------------------------------------------------------
# Condivisione delle evidenze fra siti (stessa regola dei documenti: l'evidenza
# resta del sito proprietario, i siti con cui è condivisa la vedono, la
# scaricano e la collegano ai propri controlli).
# ---------------------------------------------------------------------------

def evidence_available_to_plant_q(plant_id) -> Q:
    """Evidenze utilizzabili da un sito: sue, di organizzazione (plant null) o
    condivise con esso. Il join sul M2M può duplicare le righe: `.distinct()`."""
    return Q(plant_id=plant_id) | Q(plant__isnull=True) | Q(shared_plants=plant_id)


def evidences_visible_to(user, qs=None):
    """Evidenze leggibili dall'utente: dei suoi siti, condivise con i suoi siti
    o di organizzazione. Scope org / superuser: tutte."""
    from core.scoping import get_user_plant_ids

    qs = Evidence.objects.all() if qs is None else qs
    plant_ids = get_user_plant_ids(user)
    if plant_ids is None:
        return qs
    return qs.filter(
        Q(plant_id__in=plant_ids) | Q(shared_plants__in=plant_ids) | Q(plant__isnull=True)
    ).distinct()


def evidences_manageable_by(user, qs=None):
    """Evidenze che l'utente può modificare, eliminare o condividere: dei suoi
    siti o di organizzazione. Il sito che la riceve in condivisione la usa, ma
    non la gestisce."""
    from core.scoping import scope_queryset_by_plant

    qs = Evidence.objects.all() if qs is None else qs
    return scope_queryset_by_plant(qs, user, plant_field="plant", allow_null_plant=True)


def share_evidence(evidence, plant_ids, user) -> list:
    """Imposta i siti con cui l'evidenza è condivisa (`plant_ids` sostituisce
    l'elenco). Chi non ha scope org agisce solo sui siti a cui ha accesso: le
    condivisioni verso gli altri siti restano come sono."""
    from apps.plants.models import Plant
    from core.scoping import get_user_plant_ids

    if evidence.plant_id is None:
        raise ValidationError(
            _("Un'evidenza di organizzazione è già disponibile per tutti i siti.")
        )
    try:
        requested = set(
            Plant.objects.filter(pk__in=list(plant_ids or []), deleted_at__isnull=True)
            .exclude(pk=evidence.plant_id)
            .values_list("pk", flat=True)
        )
    except (ValidationError, ValueError, TypeError):
        raise ValidationError(_("Elenco dei siti non valido.")) from None

    current = set(evidence.shared_plants.values_list("pk", flat=True))
    accessible = get_user_plant_ids(user)
    if accessible is not None:
        accessible = set(accessible)
        requested = (requested & accessible) | (current - accessible)

    evidence.shared_plants.set(requested)
    log_action(
        user=user,
        action_code="evidence.shared",
        level="L2",
        entity=evidence,
        payload={
            "plant_ids": sorted(str(p) for p in requested),
            "added": sorted(str(p) for p in requested - current),
            "removed": sorted(str(p) for p in current - requested),
        },
    )
    return list(Plant.objects.filter(pk__in=requested).order_by("code"))


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

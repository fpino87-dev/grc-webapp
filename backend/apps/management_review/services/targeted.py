"""Riesame mirato: documenti da decidere in seduta.

Il riesame mirato è la riunione dell'organo su punti specifici fra un riesame
completo (ISO 27001 §9.3) e l'altro. Oltre ai punti liberi, l'organo decide sui
documenti in attesa: si scelgono da un elenco calcolato sui dati correnti,
ognuno diventa un punto con la revisione esaminata fissata alla selezione, e
l'esito (approvato / rinviato / respinto) si applica al documento quando il
riesame viene approvato.
"""
from django.core.exceptions import ValidationError
from django.db.models import Prefetch, Q
from django.utils.translation import gettext as _

from core.audit import log_action

from ..agenda import ISO_AGENDA_CODES
from ..models import ManagementReview, ReviewAgendaItem

DOCUMENT_ITEM_CODE = "document"
# Ordine dell'elenco: prima ciò che è più vicino alla decisione.
_STATUS_ORDER = {"approvazione": 0, "revisione": 1, "bozza": 2, "approvato": 3}


def ensure_targeted(review: ManagementReview) -> None:
    if not review.is_targeted:
        raise ValidationError(_("Operazione disponibile solo nel riesame mirato."))


def _ensure_editable(review: ManagementReview) -> None:
    if review.approval_status == "approvato":
        raise ValidationError(_("Il riesame è approvato: il verbale non è più modificabile."))
    if review.status == "completato":
        raise ValidationError(_("La riunione è chiusa: l'ordine del giorno non si modifica più."))


def _version_label(version) -> str | None:
    if version is None:
        return None
    return version.version_label or f"v{version.version_number}"


def _policies_by_type():
    """Policy di workflow attive, raggruppate per tipo di documento: si
    risolvono in memoria (sito → BU → organizzazione) come
    `resolve_document_workflow_policy`, senza una query per documento."""
    from apps.governance.models import DocumentWorkflowPolicy

    grouped = {}
    for p in DocumentWorkflowPolicy.objects.filter(deleted_at__isnull=True):
        grouped.setdefault(p.document_type, []).append(p)
    return grouped


def _match_policy(policies, plant):
    if plant is not None:
        for p in policies:
            if p.scope_type == "plant" and p.scope_id == plant.pk:
                return p
        bu_id = getattr(plant, "bu_id", None)
        if bu_id:
            for p in policies:
                if p.scope_type == "bu" and p.scope_id == bu_id:
                    return p
    return next((p for p in policies if p.scope_type == "org"), None)


def _pending_documents(review: ManagementReview, user) -> list:
    """Documenti del perimetro del riesame su cui l'organo può decidere, con
    l'ultima versione: in bozza / revisione / approvazione, oppure in vigore
    con una versione caricata dopo l'ultima approvazione. Esclusi quelli la cui
    ultima revisione è già stata respinta: tornano con la revisione successiva."""
    from apps.documents.models import Document, DocumentApproval, DocumentVersion
    from apps.documents.services import PENDING_STATUSES
    from core.scoping import scope_queryset_by_plant

    qs = Document.objects.filter(deleted_at__isnull=True)
    # Stesso perimetro dello snapshot del riesame: il sito, o l'organizzazione.
    if review.plant_id:
        qs = qs.filter(plant_id=review.plant_id)
    qs = scope_queryset_by_plant(qs, user, allow_null_plant=True)
    qs = (
        qs.filter(Q(status__in=PENDING_STATUSES) | Q(status="approvato"))
        .select_related("plant")
        .prefetch_related(
            Prefetch(
                "versions",
                queryset=DocumentVersion.objects.filter(deleted_at__isnull=True).order_by("-version_number"),
                to_attr="ordered_versions",
            ),
            Prefetch(
                "approvals",
                queryset=DocumentApproval.objects.filter(
                    deleted_at__isnull=True, action__in=["approve", "reject"], version__isnull=False,
                ).order_by("-created_at"),
                to_attr="version_decisions",
            ),
        )
    )

    result = []
    for doc in qs:
        latest = doc.ordered_versions[0] if doc.ordered_versions else None
        decisions = doc.version_decisions
        if latest is not None and any(d.action == "reject" and d.version_id == latest.pk for d in decisions):
            continue
        new_version = False
        if doc.status == "approvato":
            approved = next((d for d in decisions if d.action == "approve"), None)
            # Un'approvazione senza versione registrata (storica) non dice cosa
            # sia in vigore: come `has_unapproved_version`, non si segnala.
            if approved is None or latest is None or approved.version_id == latest.pk:
                continue
            new_version = True
        result.append((doc, latest, new_version))
    return result


def pending_documents(review: ManagementReview, user) -> list[dict]:
    """Elenco selezionabile dei documenti in attesa (endpoint pending-documents)."""
    ensure_targeted(review)
    policies = _policies_by_type()
    selected = set(
        review.agenda_items.filter(deleted_at__isnull=True, document__isnull=False)
        .values_list("document_id", flat=True)
    )
    rows = []
    for doc, latest, new_version in _pending_documents(review, user):
        policy = _match_policy(policies.get(doc.document_type, []), doc.plant)
        rows.append({
            "id": str(doc.pk),
            "document_code": doc.document_code,
            "title": doc.title,
            "document_type": doc.document_type,
            "status": doc.status,
            "is_mandatory": doc.is_mandatory,
            "plant_code": doc.plant.code if doc.plant_id else None,
            "version": _version_label(latest),
            "has_version": latest is not None,
            "new_version": new_version,
            "requires_body_resolution": bool(policy and policy.requires_body_resolution),
            "selected": doc.pk in selected,
        })
    rows.sort(key=lambda r: (
        not r["is_mandatory"], _STATUS_ORDER.get(r["status"], 9),
        (r["document_code"] or "").lower(), r["title"].lower(),
    ))
    return rows


def add_document_items(review: ManagementReview, document_ids, user) -> dict:
    """Mette all'ordine del giorno i documenti scelti, uno per punto, fissando
    la revisione esaminata (l'ultima caricata). Salta con motivo quelli non
    selezionabili invece di fallire l'intera richiesta."""
    ensure_targeted(review)
    _ensure_editable(review)
    ids = [str(i) for i in (document_ids or []) if i]
    if not ids:
        raise ValidationError(_("Nessun documento indicato."))

    pending = {str(doc.pk): (doc, latest) for doc, latest, _new in _pending_documents(review, user)}
    already = set(
        str(i) for i in review.agenda_items.filter(deleted_at__isnull=True, document__isnull=False)
        .values_list("document_id", flat=True)
    )
    last = review.agenda_items.order_by("-order").first()
    order = (last.order + 1) if last else 0

    added, skipped = [], []
    for doc_id in dict.fromkeys(ids):
        if doc_id in already:
            skipped.append({"id": doc_id, "reason": _("Già all'ordine del giorno.")})
            continue
        entry = pending.get(doc_id)
        if entry is None:
            skipped.append({"id": doc_id, "reason": _("Documento non in attesa di decisione o fuori perimetro.")})
            continue
        doc, latest = entry
        if latest is None:
            skipped.append({"id": doc_id, "title": doc.title,
                            "reason": _("Il documento non ha ancora un file caricato.")})
            continue
        label = f"[{doc.document_code}] {doc.title}" if doc.document_code else doc.title
        item = ReviewAgendaItem.objects.create(
            review=review, code=DOCUMENT_ITEM_CODE, title=label[:200], order=order,
            document=doc, document_version=latest, created_by=user,
        )
        order += 1
        added.append(item)
        log_action(
            user=user, action_code="management_review.document_item.added", level="L2", entity=item,
            payload={"review_id": str(review.pk), "document_id": doc_id, "version_id": str(latest.pk)},
        )
    return {"added": added, "skipped": skipped}


def latest_version(document):
    return document.versions.filter(deleted_at__isnull=True).order_by("-version_number").first()


def refresh_item_version(item: ReviewAgendaItem, user) -> ReviewAgendaItem:
    """Allinea il punto all'ultima revisione caricata. L'esito già registrato
    si azzera: l'organo deve decidere sul testo nuovo."""
    ensure_targeted(item.review)
    _ensure_editable(item.review)
    if item.code != DOCUMENT_ITEM_CODE or item.document_id is None:
        raise ValidationError(_("Il punto non riguarda un documento."))
    latest = latest_version(item.document)
    if latest is None or latest.pk == item.document_version_id:
        raise ValidationError(_("Il punto è già sull'ultima revisione del documento."))
    previous = item.document_version
    item.document_version = latest
    item.document_outcome = ""
    item.save(update_fields=["document_version", "document_outcome", "updated_at"])
    log_action(
        user=user, action_code="management_review.document_item.refreshed", level="L2", entity=item,
        payload={
            "review_id": str(item.review_id), "document_id": str(item.document_id),
            "from_version": _version_label(previous), "to_version": _version_label(latest),
        },
    )
    return item


def validate_document_outcome(item: ReviewAgendaItem, outcome: str) -> str:
    """Esito del punto documento: solo sui punti documento, e solo se il punto
    è sulla revisione corrente (una revisione più recente va prima riallineata)."""
    outcome = outcome or ""
    if item.code != DOCUMENT_ITEM_CODE:
        raise ValidationError(_("L'esito si registra solo sui punti relativi a un documento."))
    if outcome and outcome not in dict(ReviewAgendaItem.OUTCOME_CHOICES):
        raise ValidationError(_("Esito non valido."))
    if outcome:
        latest = latest_version(item.document)
        if latest is not None and latest.pk != item.document_version_id:
            raise ValidationError(
                _("Dopo la selezione è stata caricata una nuova revisione del documento: "
                  "riallinea il punto prima di registrare l'esito.")
            )
    return outcome


def uncovered_targeted_items(review: ManagementReview) -> list[str]:
    """Punti documento senza esito (ne blocca la chiusura)."""
    return [
        str(i.pk) for i in review.agenda_items.filter(
            deleted_at__isnull=True, code=DOCUMENT_ITEM_CODE, document_outcome="",
        )
    ]


def first_custom_order(review: ManagementReview) -> int:
    """Ordine del primo punto aggiunto a mano: dopo i punti §9.3.2 nel
    riesame completo, dall'inizio nel mirato."""
    return 0 if review.is_targeted else len(ISO_AGENDA_CODES)

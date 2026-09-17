"""Ciclo di vita del riesame: creazione, ordine del giorno, partecipanti,
decisioni (con task/PDCA collegati), chiusura e approvazione."""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext as _

from core.audit import log_action

from ..agenda import ISO_AGENDA_CODES
from ..models import ManagementReview, ReviewAction, ReviewAgendaItem
from .snapshot import get_kpi_snapshot

# Campi che fanno parte del verbale: non modificabili dopo l'approvazione.
MINUTES_FIELDS = {"title", "review_date", "plant", "chair", "attendees", "next_review_date"}


def _is_approved(review: ManagementReview) -> bool:
    return review.approval_status == "approvato"


def _ensure_not_approved(review: ManagementReview, message=None) -> None:
    if _is_approved(review):
        raise ValidationError(message or _("Il riesame è approvato: il verbale non è più modificabile."))


# ── Creazione e ordine del giorno ─────────────────────────────────────────────

def ensure_iso_agenda(review: ManagementReview, user=None) -> None:
    """Crea i punti obbligatori §9.3.2 mancanti (idempotente)."""
    existing = set(review.agenda_items.values_list("code", flat=True))
    ReviewAgendaItem.objects.bulk_create([
        ReviewAgendaItem(review=review, code=code, order=i, mandatory=True, created_by=user)
        for i, code in enumerate(ISO_AGENDA_CODES)
        if code not in existing
    ])


@transaction.atomic
def create_review(serializer, user) -> ManagementReview:
    review = serializer.save(created_by=user)
    ensure_iso_agenda(review, user)
    log_action(
        user=user,
        action_code="management_review.review.create",
        level="L2",
        entity=review,
        payload={"id": str(review.id), "title": review.title},
    )
    return review


def update_review(serializer, user) -> ManagementReview:
    review = serializer.instance
    if MINUTES_FIELDS & set(serializer.validated_data.keys()):
        _ensure_not_approved(
            review, _("Il riesame è approvato: dati della riunione e partecipanti non sono più modificabili.")
        )
    return serializer.save()


def add_agenda_item(review: ManagementReview, title: str, user) -> ReviewAgendaItem:
    _ensure_not_approved(review)
    title = (title or "").strip()
    if not title:
        raise ValidationError(_("Indicare il titolo del punto."))
    last = review.agenda_items.order_by("-order").first()
    item = ReviewAgendaItem.objects.create(
        review=review, code="custom", title=title[:200],
        order=(last.order + 1) if last else len(ISO_AGENDA_CODES), created_by=user,
    )
    log_action(
        user=user, action_code="management_review.agenda.add", level="L2", entity=item,
        payload={"review_id": str(review.pk)},
    )
    return item


def update_agenda_item(item: ReviewAgendaItem, data: dict, user) -> ReviewAgendaItem:
    _ensure_not_approved(item.review)
    fields = []
    if "discussion" in data:
        item.discussion = data["discussion"] or ""
        fields.append("discussion")
    if "title" in data and item.code == "custom":
        title = (data["title"] or "").strip()
        if not title:
            raise ValidationError(_("Indicare il titolo del punto."))
        item.title = title[:200]
        fields.append("title")
    if fields:
        item.save(update_fields=[*fields, "updated_at"])
        log_action(
            user=user, action_code="management_review.agenda.update", level="L3", entity=item,
            payload={"review_id": str(item.review_id), "fields": fields},
        )
    return item


def delete_agenda_item(item: ReviewAgendaItem, user) -> None:
    _ensure_not_approved(item.review)
    if item.mandatory:
        raise ValidationError(_("I punti obbligatori ISO 27001 §9.3 non si possono eliminare."))
    item.decisions.update(agenda_item=None)
    item.soft_delete()
    log_action(
        user=user, action_code="management_review.agenda.delete", level="L2", entity=item,
        payload={"review_id": str(item.review_id)},
    )


# ── Partecipanti ──────────────────────────────────────────────────────────────

def suggest_chair(plant_id=None):
    """Titolare suggerito per presiedere il riesame.

    CISO nominato sul sito, altrimenti CISO a livello organizzazione, altrimenti
    ISMS Manager (stesso ordine). Solo un suggerimento: l'utente può cambiarlo.
    """
    from apps.governance.services import _active_role_qs

    for role in ("ciso", "isms_manager"):
        qs = _active_role_qs(role).select_related("user").order_by("valid_from")
        if plant_id:
            hit = qs.filter(scope_type="plant", scope_id=plant_id).first()
            if hit:
                return hit.user
        hit = qs.filter(scope_type="org").first()
        if hit:
            return hit.user
    return None


# ── Decisioni (output §9.3.3) ─────────────────────────────────────────────────

@transaction.atomic
def create_review_action(serializer, user, *, create_task=False, task_role="", create_pdca=False,
                         pdca_plant=None) -> ReviewAction:
    """Registra una decisione; opzionalmente apre un task (M08, assegnato a un
    ruolo) e/o un ciclo PDCA (M11) collegati."""
    from apps.pdca.services import create_cycle
    from apps.tasks.services import create_task as create_m08_task

    review = serializer.validated_data["review"]
    _ensure_not_approved(review, _("Il riesame è approvato: non si possono aggiungere decisioni."))
    agenda_item = serializer.validated_data.get("agenda_item")
    if agenda_item and agenda_item.review_id != review.pk:
        raise ValidationError(_("Il punto all'ordine del giorno appartiene a un altro riesame."))

    action = serializer.save(created_by=user)
    description = action.description.strip()
    title = description.splitlines()[0][:120] if description else _("Decisione del riesame")
    fields = []

    if create_task:
        if not task_role:
            raise ValidationError(_("Indicare il ruolo a cui assegnare il task."))
        if not action.due_date:
            raise ValidationError(_("Per creare il task indicare la scadenza della decisione."))
        action.task = create_m08_task(
            plant=review.plant,
            title=_("Riesame di direzione: %(title)s") % {"title": title},
            description=description,
            priority="alta" if action.decision_type == "modifica_sgsi" else "media",
            source_module="M13",
            source_id=review.pk,
            due_date=action.due_date,
            assign_type="role",
            assign_value=task_role,
        )
        fields.append("task")

    if create_pdca:
        plant = review.plant or pdca_plant
        if plant is None:
            raise ValidationError(_("Per un riesame di organizzazione indicare il sito del ciclo PDCA."))
        action.pdca_cycle = create_cycle(
            plant=plant, title=title, trigger_type="management_review", trigger_source_id=review.pk,
        )
        fields.append("pdca_cycle")

    if fields:
        action.save(update_fields=[*fields, "updated_at"])

    log_action(
        user=user,
        action_code="management_review.action.create",
        level="L2",
        entity=action,
        payload={
            "id": str(action.id), "review_id": str(review.pk),
            "task_id": str(action.task_id) if action.task_id else None,
            "pdca_id": str(action.pdca_cycle_id) if action.pdca_cycle_id else None,
        },
    )
    return action


def update_review_action(serializer, user) -> ReviewAction:
    """Dopo l'approvazione resta aggiornabile solo l'avanzamento (stato)."""
    action = serializer.instance
    changed = set(serializer.validated_data.keys())
    if _is_approved(action.review) and changed - {"status", "closed_at"}:
        raise ValidationError(_("Il riesame è approvato: della decisione si può aggiornare solo lo stato."))
    if "status" in changed:
        new_status = serializer.validated_data["status"]
        serializer.validated_data["closed_at"] = timezone.now() if new_status == "chiuso" else None
    return serializer.save()


def delete_review_action(action: ReviewAction, user) -> None:
    _ensure_not_approved(action.review, _("Il riesame è approvato: le decisioni non si possono eliminare."))
    log_action(
        user=user, action_code="management_review.action.delete", level="L2", entity=action,
        payload={"id": str(action.id), "review_id": str(action.review_id)},
    )
    action.soft_delete()


# ── Stato riunione, chiusura, approvazione ────────────────────────────────────

def start_review(review: ManagementReview, user) -> ManagementReview:
    if review.status != "pianificato":
        raise ValidationError(_("La riunione è già stata avviata."))
    review.status = "in_corso"
    review.save(update_fields=["status", "updated_at"])
    log_action(
        user=user, action_code="management_review.review.start", level="L3", entity=review,
        payload={"id": str(review.id)},
    )
    return review


def uncovered_mandatory_items(review: ManagementReview) -> list[str]:
    """Codici dei punti obbligatori senza discussione né decisioni."""
    missing = []
    items = review.agenda_items.filter(mandatory=True).prefetch_related("decisions")
    for item in items:
        has_decision = any(d.deleted_at is None for d in item.decisions.all())
        if not item.discussion.strip() and not has_decision:
            missing.append(item.code)
    return missing


def complete_review(review: ManagementReview, user) -> ManagementReview:
    """Chiude la riunione: ogni punto obbligatorio §9.3.2 deve avere almeno una
    discussione o una decisione. Propone la data del prossimo riesame."""
    from apps.compliance_schedule.services import get_due_date

    if review.status == "completato":
        raise ValidationError(_("La riunione è già completata."))
    missing = uncovered_mandatory_items(review)
    if missing:
        raise ValidationError(
            _("Prima di chiudere la riunione completare i punti obbligatori dell'ordine del giorno."),
            code="agenda_incomplete",
            params={"missing": missing},
        )

    fields = ["status", "updated_at"]
    if review.plant_id:
        review.kpi_snapshot = get_kpi_snapshot(review.plant_id)
        fields.append("kpi_snapshot")
    if not review.next_review_date:
        review.next_review_date = get_due_date("management_review", review.plant, review.review_date)
        fields.append("next_review_date")
    review.status = "completato"
    review.save(update_fields=fields)
    log_action(
        user=user,
        action_code="management_review.review.complete",
        level="L2",
        entity=review,
        payload={"id": str(review.id), "title": review.title},
    )
    return review


def approve_review(review: ManagementReview, user, note="") -> ManagementReview:
    """Approva formalmente il riesame di direzione."""
    if review.approval_status == "approvato":
        raise ValidationError(_("Il riesame è già approvato."))
    if not review.snapshot_generated_at:
        raise ValidationError(
            _("Generare lo snapshot dei dati prima di approvare il riesame.")
        )
    if review.status != "completato":
        raise ValidationError(_("Chiudere la riunione prima di approvare il riesame."))

    review.approval_status = "approvato"
    review.approved_by = user
    review.approved_at = timezone.now()
    review.approval_note = note
    review.save(update_fields=[
        "approval_status", "approved_by", "approved_at",
        "approval_note", "updated_at",
    ])

    log_action(
        user=user,
        action_code="management_review.approved",
        level="L1",
        entity=review,
        payload={"review_id": str(review.pk), "note": (note or "")[:200]},
    )
    return review

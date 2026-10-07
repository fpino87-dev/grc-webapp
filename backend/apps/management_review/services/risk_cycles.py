"""Riesame (completo o mirato): valutazioni dei rischi da approvare.

La procedura di risk management (§5) chiede che l'organo approvi la
valutazione del registro e il piano di trattamento. La valutazione inviata
in approvazione dal modulo Risk diventa un punto all'ordine del giorno con il
suo esito, e l'esito si applica al registro quando il verbale viene
approvato: approvata → il registro si congela con l'organo e il riesame del
verbale; respinta → torna in corso; rinviata → resta in approvazione.
"""
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext as _

from core.audit import log_action

from ..models import ManagementReview, ReviewAgendaItem
from .risk_acceptances import _ensure_editable

RISK_CYCLE_ITEM_CODE = "risk_cycle"


def _pending_cycles(review: ManagementReview, user) -> list:
    """Valutazioni che l'organo di questo riesame può approvare, visibili a
    chi consulta, escluse quelle già all'ordine del giorno di un altro
    riesame non ancora approvato (una decisione alla volta)."""
    from apps.risk.services import cycles_awaiting_body
    from core.scoping import user_can_access_plant, user_has_org_scope

    busy = set(
        ReviewAgendaItem.objects.filter(
            deleted_at__isnull=True, risk_cycle__isnull=False, review__deleted_at__isnull=True,
        ).exclude(review=review).exclude(review__approval_status="approvato")
        .values_list("risk_cycle_id", flat=True)
    )
    org_scope = user_has_org_scope(user)
    out = []
    for cycle in cycles_awaiting_body(review.plant_id):
        if cycle.pk in busy:
            continue
        if org_scope if cycle.plant_id is None else user_can_access_plant(user, cycle.plant_id):
            out.append(cycle)
    return out


def _register_label(cycle) -> str:
    return f"{cycle.plant.code} — {cycle.plant.name}" if cycle.plant_id else _("Registro di gruppo")


def _item_title(cycle) -> str:
    return f"{_('Approvazione della valutazione dei rischi')} — {_register_label(cycle)}"


def cycle_info(cycle) -> dict:
    """Dati della valutazione per elenco e punto (risks_count se annotato)."""
    return {
        "id": str(cycle.pk),
        "plant_id": str(cycle.plant_id) if cycle.plant_id else None,
        "plant_code": cycle.plant.code if cycle.plant_id else None,
        "register": _register_label(cycle),
        "kind": cycle.kind,
        "status": cycle.status,
        "started_at": cycle.started_at,
        "risks_count": getattr(cycle, "risks_count", None),
    }


def pending_cycles(review: ManagementReview, user) -> list[dict]:
    """Elenco selezionabile (endpoint pending-risk-cycles)."""
    selected = set(
        review.agenda_items.filter(deleted_at__isnull=True, risk_cycle__isnull=False)
        .values_list("risk_cycle_id", flat=True)
    )
    return [{**cycle_info(c), "selected": c.pk in selected} for c in _pending_cycles(review, user)]


def add_cycle_items(review: ManagementReview, cycle_ids, user) -> dict:
    """Mette all'ordine del giorno le valutazioni scelte, una per punto.
    Salta con motivo quelle non selezionabili invece di fallire tutto."""
    _ensure_editable(review)
    ids = [str(i) for i in (cycle_ids or []) if i]
    if not ids:
        raise ValidationError(_("Nessuna valutazione indicata."))

    pending = {str(c.pk): c for c in _pending_cycles(review, user)}
    already = set(
        str(i) for i in review.agenda_items.filter(deleted_at__isnull=True, risk_cycle__isnull=False)
        .values_list("risk_cycle_id", flat=True)
    )
    last = review.agenda_items.order_by("-order").first()
    order = (last.order + 1) if last else 0

    added, skipped = [], []
    for cycle_id in dict.fromkeys(ids):
        if cycle_id in already:
            skipped.append({"id": cycle_id, "reason": _("Già all'ordine del giorno.")})
            continue
        cycle = pending.get(cycle_id)
        if cycle is None:
            skipped.append({"id": cycle_id, "reason": _(
                "Valutazione non in approvazione, fuori perimetro o già in un altro riesame.")})
            continue
        item = ReviewAgendaItem.objects.create(
            review=review, code=RISK_CYCLE_ITEM_CODE, title=_item_title(cycle)[:200], order=order,
            risk_cycle=cycle, created_by=user,
        )
        order += 1
        added.append(item)
        log_action(
            user=user, action_code="management_review.risk_cycle_item.added", level="L2", entity=item,
            payload={"review_id": str(review.pk), "cycle_id": cycle_id},
        )
    return {"added": added, "skipped": skipped}


def validate_cycle_outcome(item: ReviewAgendaItem, outcome: str) -> str:
    if outcome and item.risk_cycle.status != "in_approvazione":
        raise ValidationError(_("La valutazione non è più in approvazione (rinviata o già approvata)."))
    if outcome == "approvato" and not item.review.governing_body_id:
        raise ValidationError(_("Indicare l'organo del riesame prima di approvare la valutazione dei rischi."))
    return outcome


def apply_cycle_outcomes(review: ManagementReview, user) -> dict:
    """Applica ai registri gli esiti decisi nel riesame approvato.
    Idempotente: una valutazione nel frattempo rinviata o approvata dal
    modulo Risk non annulla l'approvazione del riesame, resta sul punto con
    il motivo."""
    from apps.risk.services import decide_cycle_in_review

    if review.approval_status != "approvato":
        raise ValidationError(_("Gli esiti si applicano quando il riesame è approvato."))

    items = (
        review.agenda_items.filter(
            deleted_at__isnull=True, code=RISK_CYCLE_ITEM_CODE, document_outcome_applied_at__isnull=True,
        )
        .exclude(document_outcome="")
        .select_related("risk_cycle", "risk_cycle__plant")
        .order_by("order")
    )
    applied, skipped = [], []
    for item in items:
        cycle = item.risk_cycle
        error = ""
        if item.document_outcome in ("approvato", "respinto"):
            try:
                decide_cycle_in_review(
                    user, cycle, review=review, approved=item.document_outcome == "approvato",
                    note=item.discussion,
                )
            except ValidationError as exc:
                error = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
        if error:
            item.document_outcome_error = error[:300]
            item.save(update_fields=["document_outcome_error", "updated_at"])
            skipped.append({"item_id": str(item.pk), "cycle_id": str(cycle.pk),
                            "outcome": item.document_outcome, "reason": error})
            continue
        item.document_outcome_applied_at = timezone.now()
        item.document_outcome_error = ""
        item.save(update_fields=["document_outcome_applied_at", "document_outcome_error", "updated_at"])
        applied.append({"item_id": str(item.pk), "cycle_id": str(cycle.pk), "outcome": item.document_outcome})

    if applied or skipped:
        log_action(
            user=user, action_code="management_review.risk_cycle_outcomes_applied", level="L2",
            entity=review,
            payload={
                "review_id": str(review.pk),
                "approved": [a["cycle_id"] for a in applied if a["outcome"] == "approvato"],
                "rejected": [a["cycle_id"] for a in applied if a["outcome"] == "respinto"],
                "postponed": [a["cycle_id"] for a in applied if a["outcome"] == "rinviato"],
                "skipped": [s["cycle_id"] for s in skipped],
            },
        )
    return {"applied": applied, "skipped": skipped}

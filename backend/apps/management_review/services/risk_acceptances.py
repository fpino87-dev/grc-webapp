"""Riesame (completo o mirato): accettazioni del rischio da deliberare.

La procedura di risk management (§10) riserva all'organo l'accettazione dei
rischi che la policy gli assegna e di quelli che il Risk Owner ha valutato e
tratta da solo. L'organo decide nel riesame di direzione: si scelgono le
accettazioni in attesa da un elenco calcolato sui dati correnti, ognuna
diventa un punto all'ordine del giorno con il suo esito, e l'esito si applica
all'accettazione quando il verbale viene approvato.
"""
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext as _

from core.audit import log_action

from ..models import ManagementReview, ReviewAgendaItem

RISK_ACCEPTANCE_ITEM_CODE = "risk_acceptance"


def _ensure_editable(review: ManagementReview) -> None:
    if review.approval_status == "approvato":
        raise ValidationError(_("Il riesame è approvato: il verbale non è più modificabile."))
    if review.status == "completato":
        raise ValidationError(_("La riunione è chiusa: l'ordine del giorno non si modifica più."))


def _pending_acceptances(review: ManagementReview, user) -> list:
    """Accettazioni che l'organo di questo riesame può decidere, visibili a
    chi consulta, escluse quelle già all'ordine del giorno di un altro
    riesame non ancora approvato (una decisione alla volta)."""
    from apps.risk.services import acceptances_awaiting_body
    from core.scoping import user_can_access_plant, user_has_org_scope

    busy = set(
        ReviewAgendaItem.objects.filter(
            deleted_at__isnull=True, risk_acceptance__isnull=False, review__deleted_at__isnull=True,
        ).exclude(review=review).exclude(review__approval_status="approvato")
        .values_list("risk_acceptance_id", flat=True)
    )
    org_scope = user_has_org_scope(user)
    visible = {}
    out = []
    for acc in acceptances_awaiting_body(review.plant_id):
        if acc.pk in busy:
            continue
        plant_id = acc.risk.plant_id
        if plant_id not in visible:
            visible[plant_id] = org_scope if plant_id is None else user_can_access_plant(user, plant_id)
        if visible[plant_id]:
            out.append(acc)
    return out


def _item_title(acc) -> str:
    from apps.risk.services import risk_label

    code = acc.risk.plant.code if acc.risk.plant_id else _("Gruppo")
    return f"{_('Accettazione del rischio')} — {risk_label(acc.risk)} ({code})"


def pending_acceptances(review: ManagementReview, user) -> list[dict]:
    """Elenco selezionabile (endpoint pending-acceptances)."""
    from apps.risk.services import class_rank, risk_label

    selected = set(
        review.agenda_items.filter(deleted_at__isnull=True, risk_acceptance__isnull=False)
        .values_list("risk_acceptance_id", flat=True)
    )
    rows = [{
        "id": str(acc.pk),
        "risk_id": str(acc.risk_id),
        "risk_name": risk_label(acc.risk),
        "plant_code": acc.risk.plant.code if acc.risk.plant_id else None,
        "risk_class": acc.risk_class,
        "rationale": acc.rationale,
        "expires_on": acc.expires_on,
        "upper_opinion": acc.upper_opinion,
        "requested_at": acc.created_at,
        "selected": acc.pk in selected,
    } for acc in _pending_acceptances(review, user)]
    rows.sort(key=lambda r: (-class_rank(r["risk_class"]), r["plant_code"] or "", r["risk_name"].lower()))
    return rows


def add_acceptance_items(review: ManagementReview, acceptance_ids, user) -> dict:
    """Mette all'ordine del giorno le accettazioni scelte, una per punto.
    Salta con motivo quelle non selezionabili invece di fallire tutto."""
    _ensure_editable(review)
    ids = [str(i) for i in (acceptance_ids or []) if i]
    if not ids:
        raise ValidationError(_("Nessuna accettazione indicata."))

    pending = {str(acc.pk): acc for acc in _pending_acceptances(review, user)}
    already = set(
        str(i) for i in review.agenda_items.filter(deleted_at__isnull=True, risk_acceptance__isnull=False)
        .values_list("risk_acceptance_id", flat=True)
    )
    last = review.agenda_items.order_by("-order").first()
    order = (last.order + 1) if last else 0

    added, skipped = [], []
    for acc_id in dict.fromkeys(ids):
        if acc_id in already:
            skipped.append({"id": acc_id, "reason": _("Già all'ordine del giorno.")})
            continue
        acc = pending.get(acc_id)
        if acc is None:
            skipped.append({"id": acc_id, "reason": _(
                "Accettazione non in attesa dell'organo, fuori perimetro o già in un altro riesame.")})
            continue
        item = ReviewAgendaItem.objects.create(
            review=review, code=RISK_ACCEPTANCE_ITEM_CODE, title=_item_title(acc)[:200], order=order,
            risk_acceptance=acc, created_by=user,
        )
        order += 1
        added.append(item)
        log_action(
            user=user, action_code="management_review.risk_acceptance_item.added", level="L2", entity=item,
            payload={"review_id": str(review.pk), "acceptance_id": acc_id},
        )
    return {"added": added, "skipped": skipped}


def validate_acceptance_outcome(item: ReviewAgendaItem, outcome: str) -> str:
    if outcome and item.risk_acceptance.status != "pending":
        raise ValidationError(_("L'accettazione non è più in attesa di decisione (revocata, respinta o scaduta)."))
    return outcome


def apply_acceptance_outcomes(review: ManagementReview, user) -> dict:
    """Applica alle accettazioni gli esiti decisi nel riesame approvato.

    - approvato → l'accettazione registra la delibera e si attiva (se non
      manca il parere vincolante);
    - respinto → l'accettazione si chiude come respinta;
    - rinviato → nessun cambio: resta in attesa per un riesame successivo.

    Idempotente come per i documenti: un'accettazione nel frattempo revocata
    o scaduta non annulla l'approvazione del riesame, resta sul punto con il
    motivo.
    """
    from apps.risk.services import decide_acceptance_in_review

    if review.approval_status != "approvato":
        raise ValidationError(_("Gli esiti si applicano quando il riesame è approvato."))

    items = (
        review.agenda_items.filter(
            deleted_at__isnull=True, code=RISK_ACCEPTANCE_ITEM_CODE,
            document_outcome_applied_at__isnull=True,
        )
        .exclude(document_outcome="")
        .select_related("risk_acceptance", "risk_acceptance__risk", "risk_acceptance__risk__plant")
        .order_by("order")
    )
    applied, skipped = [], []
    for item in items:
        acc = item.risk_acceptance
        error = ""
        if item.document_outcome in ("approvato", "respinto"):
            try:
                decide_acceptance_in_review(
                    user, acc, review=review, approved=item.document_outcome == "approvato",
                    note=item.discussion,
                )
            except ValidationError as exc:
                error = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
        if error:
            item.document_outcome_error = error[:300]
            item.save(update_fields=["document_outcome_error", "updated_at"])
            skipped.append({"item_id": str(item.pk), "acceptance_id": str(acc.pk),
                            "outcome": item.document_outcome, "reason": error})
            continue
        item.document_outcome_applied_at = timezone.now()
        item.document_outcome_error = ""
        item.save(update_fields=["document_outcome_applied_at", "document_outcome_error", "updated_at"])
        applied.append({"item_id": str(item.pk), "acceptance_id": str(acc.pk), "outcome": item.document_outcome})

    if applied or skipped:
        log_action(
            user=user, action_code="management_review.risk_acceptance_outcomes_applied", level="L2",
            entity=review,
            payload={
                "review_id": str(review.pk),
                "approved": [a["acceptance_id"] for a in applied if a["outcome"] == "approvato"],
                "rejected": [a["acceptance_id"] for a in applied if a["outcome"] == "respinto"],
                "postponed": [a["acceptance_id"] for a in applied if a["outcome"] == "rinviato"],
                "skipped": [s["acceptance_id"] for s in skipped],
            },
        )
    return {"applied": applied, "skipped": skipped}

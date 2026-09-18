"""Ciclo di vita del riesame: creazione, ordine del giorno, partecipanti,
decisioni (con task/PDCA collegati), chiusura e approvazione."""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext as _

from core.audit import log_action

from ..agenda import ISO_AGENDA_CODES
from ..models import ManagementReview, ReviewAction, ReviewAgendaItem, ReviewParticipant
from .snapshot import get_kpi_snapshot

# Campi che fanno parte del verbale: non modificabili dopo l'approvazione.
MINUTES_FIELDS = {"title", "review_date", "plant", "governing_body", "next_review_date"}


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


def _validate_governing_body(body, plant) -> None:
    """L'organo deve governare il perimetro del riesame: un riesame di sito
    può essere tenuto da un organo di organizzazione o da uno che include il
    sito; un riesame di organizzazione solo da un organo di organizzazione."""
    from apps.governance.services import committee_covers_plant

    if body is None:
        return
    if plant is None:
        if body.plants.exists():
            raise ValidationError(_("Un riesame di organizzazione va tenuto da un organo di organizzazione."))
    elif not committee_covers_plant(body, plant.pk):
        raise ValidationError(_("L'organo scelto non governa il sito del riesame."))


@transaction.atomic
def create_review(serializer, user) -> ManagementReview:
    data = serializer.validated_data
    _validate_governing_body(data.get("governing_body"), data.get("plant"))
    review = serializer.save(created_by=user)
    ensure_iso_agenda(review, user)
    # Convocati proposti: i componenti in carica dell'organo o, in mancanza di
    # un organo, il CISO come presidente (si correggono dal dettaglio).
    if review.governing_body_id:
        participants_from_body(review, user, audit=False)
    else:
        chair = suggest_chair(review.plant_id)
        if chair is not None:
            ReviewParticipant.objects.create(
                review=review, user=chair, full_name=_user_label(chair),
                body_role="presidente", is_chair=True, created_by=user,
            )
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
    data = serializer.validated_data
    if MINUTES_FIELDS & set(data.keys()):
        _ensure_not_approved(
            review, _("Il riesame è approvato: dati della riunione e partecipanti non sono più modificabili.")
        )
    if "governing_body" in data or "plant" in data:
        _validate_governing_body(
            data.get("governing_body", review.governing_body), data.get("plant", review.plant)
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

def _user_label(u) -> str:
    return f"{u.first_name} {u.last_name}".strip() or u.email


def participants_from_body(review: ManagementReview, user, audit=True) -> list:
    """Sostituisce i convocati con i componenti dell'organo in carica alla data
    del riesame (tutti «presente»: si correggono le assenze dopo)."""
    from apps.governance.services import active_members

    _ensure_not_approved(review)
    if not review.governing_body_id:
        raise ValidationError(_("Il riesame non è collegato a un organo di governo."))
    day = review.review_date or timezone.localdate()
    for p in review.participants.all():
        p.soft_delete()
    created = [
        ReviewParticipant.objects.create(
            review=review, member=m, user=m.user, full_name=m.full_name, position=m.position,
            body_role=m.body_role, is_chair=(m.body_role == "presidente"), order=i, created_by=user,
        )
        for i, m in enumerate(active_members(review.governing_body, day))
    ]
    if audit:
        log_action(
            user=user, action_code="management_review.participants.from_body", level="L2", entity=review,
            payload={"review_id": str(review.pk), "count": len(created)},
        )
    return created


def set_participants(review: ManagementReview, rows: list, user) -> list:
    """Sostituisce l'elenco dei convocati.

    Ogni riga è un componente dell'organo (`member`), un utente (`user`) o un
    ospite (solo nome e qualifica). Nome e qualifica si congelano qui: se non
    indicati si prendono dall'anagrafica. Un solo presidente, e presente.
    """
    from django.contrib.auth import get_user_model

    from apps.governance.models import CommitteeMember

    _ensure_not_approved(
        review, _("Il riesame è approvato: dati della riunione e partecipanti non sono più modificabili.")
    )
    if not isinstance(rows, list):
        raise ValidationError(_("Elenco partecipanti non valido."))

    User = get_user_model()
    member_ids = [r.get("member") for r in rows if isinstance(r, dict) and r.get("member")]
    user_ids = [r.get("user") for r in rows if isinstance(r, dict) and r.get("user")]
    members = {str(m.pk): m for m in CommitteeMember.objects.filter(pk__in=member_ids).select_related("user")}
    users = {str(u.pk): u for u in User.objects.filter(pk__in=user_ids)}

    roles = dict(ReviewParticipant.ROLE_CHOICES)
    attendances = dict(ReviewParticipant.ATTENDANCE_CHOICES)
    prepared, seen = [], set()
    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            raise ValidationError(_("Elenco partecipanti non valido."))
        member = members.get(str(r.get("member"))) if r.get("member") else None
        if r.get("member") and member is None:
            raise ValidationError(_("Componente dell'organo inesistente."))
        if member is not None and member.committee_id != review.governing_body_id:
            raise ValidationError(_("%(name)s non è componente dell'organo del riesame.") % {"name": member.full_name})
        linked = member.user if member is not None else None
        account = users.get(str(r.get("user"))) if r.get("user") else linked
        if r.get("user") and account is None:
            raise ValidationError(_("Utente inesistente."))

        full_name = (r.get("full_name") or "").strip() or (
            member.full_name if member else _user_label(account) if account else "")
        if not full_name:
            raise ValidationError(_("Indicare il nome di ogni partecipante."))
        key = ("m", member.pk) if member else ("u", account.pk) if account else ("n", full_name.lower())
        if key in seen:
            raise ValidationError(_("%(name)s compare due volte fra i partecipanti.") % {"name": full_name})
        seen.add(key)

        role = r.get("body_role") or (member.body_role if member else "ospite")
        attendance = r.get("attendance") or "presente"
        if role not in roles or attendance not in attendances:
            raise ValidationError(_("Ruolo o presenza non validi."))
        delegate = (r.get("delegate_name") or "").strip() if attendance == "delegato" else ""
        if attendance == "delegato" and not delegate:
            raise ValidationError(_("Indicare il delegato di %(name)s.") % {"name": full_name})
        prepared.append(ReviewParticipant(
            review=review, member=member, user=account, full_name=full_name[:200],
            position=((r.get("position") or "").strip() or (member.position if member else ""))[:200],
            body_role=role, is_chair=bool(r.get("is_chair")), attendance=attendance,
            delegate_name=delegate[:200], order=i, created_by=user,
        ))

    chairs = [p for p in prepared if p.is_chair]
    if len(chairs) > 1:
        raise ValidationError(_("Il riesame può avere un solo presidente."))
    if chairs and chairs[0].attendance != "presente":
        raise ValidationError(_("Chi presiede il riesame deve risultare presente."))

    with transaction.atomic():
        for p in review.participants.all():
            p.soft_delete()
        ReviewParticipant.objects.bulk_create(prepared)
    log_action(
        user=user, action_code="management_review.participants.update", level="L2", entity=review,
        payload={
            "review_id": str(review.pk), "count": len(prepared),
            "present": sum(1 for p in prepared if p.attendance == "presente"),
        },
    )
    return prepared


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
                         pdca_plant=None, objective=None) -> ReviewAction:
    """Registra una decisione; opzionalmente apre un task (M08, assegnato a un
    ruolo), un ciclo PDCA (M11) e/o un obiettivo di sicurezza (§6.2) collegati."""
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

    if objective:
        action.security_objective = _objective_from_decision(review, action, objective, user)
        fields.append("security_objective")

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
            "objective_id": str(action.security_objective_id) if action.security_objective_id else None,
        },
    )
    return action


def _objective_from_decision(review, action, data: dict, user):
    """Crea l'obiettivo di sicurezza deliberato dal riesame (§9.3.3 → §6.2).

    Nasce in **bozza**, non attivo: il riesame decide *che* ci sarà un
    obiettivo, ma il piano richiesto da §6.2 (risorse, metodo di valutazione)
    si completa dopo la riunione, e solo allora l'obiettivo si attiva. Così la
    delibera non produce un impegno formalmente incompleto.
    """
    from apps.governance.models import SecurityObjective
    from apps.governance.services import _validate_objective, _objective_audit

    payload = {
        "plant": review.plant,
        "code": (data.get("code") or "").strip(),
        "title": (data.get("title") or action.description.strip().splitlines()[0][:200]),
        "description": action.description,
        "origin": "riesame",
        "source_review_id": review.pk,
        "measure_source": data.get("measure_source") or "kpi",
        "kpi_definition": data.get("kpi_definition"),
        "unit": data.get("unit") or "",
        "start_date": data.get("start_date") or review.review_date,
        "baseline_value": data.get("baseline_value"),
        "target_value": data.get("target_value"),
        "target_direction": data.get("target_direction") or "above",
        "target_date": data.get("target_date") or action.due_date,
        "owner_role": data.get("owner_role") or "",
        "status": "bozza",
    }
    if not payload["code"]:
        raise ValidationError(_("Indicare il codice dell'obiettivo di sicurezza."))
    if payload["target_value"] is None:
        raise ValidationError(_("Indicare il valore target dell'obiettivo."))
    if not payload["target_date"]:
        raise ValidationError(_("Indicare la scadenza dell'obiettivo (o quella della decisione)."))

    _validate_objective(payload)
    objective = SecurityObjective.objects.create(created_by=user, **payload)
    _objective_audit(user, objective, "create", {
        "origin": "riesame", "review_id": str(review.pk), "decision_id": str(action.pk),
    })
    return objective


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


def approving_member(review: ManagementReview, user):
    """Il componente in carica dell'organo del riesame collegato a `user`."""
    from django.db.models import Q

    if not review.governing_body_id or user is None or not getattr(user, "is_authenticated", False):
        return None
    today = timezone.localdate()
    return (
        review.governing_body.members.filter(user=user, valid_from__lte=today)
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today)).first()
    )


def can_approve(review: ManagementReview, user) -> bool:
    from core.permissions import user_has_any_role

    from ..permissions import ManagementReviewPermission

    return (
        user_has_any_role(user, ManagementReviewPermission.write_roles)
        or approving_member(review, user) is not None
    )


def approve_review(review: ManagementReview, user, note="", *, mode="in_app",
                   resolution_ref="", resolution_date=None, document_id=None) -> ManagementReview:
    """Approva formalmente il riesame di direzione (§9.3).

    - ``in_app``: approva chi preme il pulsante. Se è un componente in carica
      dell'organo, l'approvazione è sua; altrimenti deve essere governance.
    - ``delibera``: governance registra l'approvazione deliberata dall'organo,
      con estremi della delibera (numero e data) ed eventuale evidenza M07.
    """
    from datetime import date as _date

    from rest_framework.exceptions import PermissionDenied

    from core.permissions import user_has_any_role

    from ..permissions import ManagementReviewPermission

    if review.approval_status == "approvato":
        raise ValidationError(_("Il riesame è già approvato."))
    if not review.snapshot_generated_at:
        raise ValidationError(
            _("Generare lo snapshot dei dati prima di approvare il riesame.")
        )
    if review.status != "completato":
        raise ValidationError(_("Chiudere la riunione prima di approvare il riesame."))

    is_governance = user_has_any_role(user, ManagementReviewPermission.write_roles)
    member = approving_member(review, user)
    fields = {"approval_mode": mode, "approved_member": None, "approval_resolution_ref": "",
              "approval_resolution_date": None, "approval_document_id": None}

    if mode == "in_app":
        if member is None and not is_governance:
            raise PermissionDenied(_("Solo un componente in carica dell'organo può approvare questo riesame."))
        fields["approved_member"] = member
    elif mode == "delibera":
        if not is_governance:
            raise PermissionDenied(_("La delibera dell'organo si registra da governance."))
        ref = (resolution_ref or "").strip()
        if isinstance(resolution_date, str) and resolution_date:
            try:
                resolution_date = _date.fromisoformat(resolution_date)
            except ValueError:
                raise ValidationError(_("Data della delibera non valida (formato atteso: AAAA-MM-GG).")) from None
        if not ref or not resolution_date:
            raise ValidationError(_("Indicare numero e data della delibera."))
        if review.review_date and resolution_date < review.review_date:
            raise ValidationError(_("La delibera non può precedere la riunione di riesame."))
        if resolution_date > timezone.localdate():
            raise ValidationError(_("La data della delibera non può essere futura."))
        if document_id:
            from apps.documents.models import Document

            from core.scoping import scope_queryset_by_plant

            visible = scope_queryset_by_plant(Document.objects.all(), user, allow_null_plant=True)
            if not visible.filter(pk=document_id).exists():
                raise ValidationError(_("Documento di evidenza inesistente o non accessibile."))
        fields.update(approval_resolution_ref=ref[:100], approval_resolution_date=resolution_date,
                      approval_document_id=document_id or None)
    else:
        raise ValidationError(_("Modalità di approvazione non valida."))

    for k, v in fields.items():
        setattr(review, k, v)
    review.approval_status = "approvato"
    review.approved_by = user
    review.approved_at = timezone.now()
    review.approval_note = note
    review.save(update_fields=[
        "approval_status", "approved_by", "approved_at", "approval_note", "updated_at", *fields.keys(),
    ])

    log_action(
        user=user,
        action_code="management_review.approved",
        level="L1",
        entity=review,
        payload={
            "review_id": str(review.pk), "note": (note or "")[:200], "mode": mode,
            "member_id": str(member.pk) if member and mode == "in_app" else None,
            "resolution_ref": fields["approval_resolution_ref"] or None,
        },
    )
    return review

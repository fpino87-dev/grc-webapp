from datetime import timedelta

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.exceptions import PermissionDenied, ValidationError

from core.audit import log_action

from .models import (
    TrainingEnrollment,
    TrainingPlanItem,
    TrainingSession,
)

# Chi gestisce piano, gruppi ed erogazioni: questi ruoli GRC oppure chi ha la
# nomina di CISO in Governance. Nessuna assegnazione: registra chi arriva prima.
MANAGER_ROLES = frozenset({"super_admin", "compliance_officer", "plant_manager"})
DUE_SOON_DAYS = 30


def get_completion_rate(course_id) -> float:
    """Return completion rate (0-100) for a given course."""
    total = TrainingEnrollment.objects.filter(course_id=course_id).count()
    if total == 0:
        return 0.0
    completed = TrainingEnrollment.objects.filter(course_id=course_id, status="completato").count()
    return round((completed / total) * 100, 2)


def get_overdue_enrollments():
    """Return enrollments where the course deadline has passed and status is not completed."""
    today = timezone.localdate()
    return TrainingEnrollment.objects.filter(
        course__deadline__lt=today,
    ).exclude(
        status__in=["completato", "scaduto"],
    ).select_related("course", "user")


# ── Permessi di gestione ────────────────────────────────────────────────────

def _active_ciso_assignments(user):
    from apps.governance.models import NormativeRole, RoleAssignment

    today = timezone.localdate()
    return RoleAssignment.objects.filter(
        user=user,
        role=NormativeRole.CISO,
        valid_from__lte=today,
        deleted_at__isnull=True,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today))


def is_training_manager(user) -> bool:
    """Può gestire la formazione su almeno un perimetro (controllo d'ingresso
    dell'endpoint; il perimetro si verifica con `can_manage_training`)."""
    from core.permissions import user_has_any_role

    if user is None or not getattr(user, "is_authenticated", False):
        return False
    return user_has_any_role(user, MANAGER_ROLES) or _active_ciso_assignments(user).exists()


def can_manage_training(user, plant) -> bool:
    """True se `user` gestisce la formazione del sito (`plant=None` = piano di
    organizzazione, che richiede un perimetro di organizzazione)."""
    from apps.auth_grc.models import UserPlantAccess

    if getattr(user, "is_superuser", False):
        return True
    for access in UserPlantAccess.objects.filter(
        user=user, role__in=MANAGER_ROLES, deleted_at__isnull=True,
    ).prefetch_related("scope_plants"):
        if access.scope_type == "org":
            return True
        if plant is None:
            continue
        if access.scope_type == "bu" and access.scope_bu_id and access.scope_bu_id == plant.bu_id:
            return True
        if access.scope_type in ("plant_list", "single_plant") and any(
            p.pk == plant.pk for p in access.scope_plants.all()
        ):
            return True
    for a in _active_ciso_assignments(user):
        if a.scope_type == "org":
            return True
        if plant is None:
            continue
        if a.scope_type == "plant" and a.scope_id == plant.pk:
            return True
        if a.scope_type == "bu" and plant.bu_id and a.scope_id == plant.bu_id:
            return True
    return False


def require_training_manage(user, plant) -> None:
    if not can_manage_training(user, plant):
        raise PermissionDenied(_("Non gestisci la formazione di questo sito."))


def _audit(user, action, entity, payload):
    # Solo identificativi e conteggi (regola #11): nessun nome, nessun titolo.
    log_action(
        user=user,
        action_code=f"training.{action}",
        level="L2",
        entity=entity,
        payload={"id": str(entity.pk), **payload},
    )


# ── Gruppi di destinatari ───────────────────────────────────────────────────

def create_audience(serializer, user):
    plant = serializer.validated_data["plant"]
    require_training_manage(user, plant)
    audience = serializer.save(created_by=user, headcount_updated_at=timezone.localdate())
    _audit(user, "audience.create", audience, {"headcount": audience.headcount})
    return audience


def update_audience(serializer, user):
    audience = serializer.instance
    require_training_manage(user, audience.plant)
    new_plant = serializer.validated_data.get("plant")
    if new_plant is not None and new_plant.pk != audience.plant_id:
        raise ValidationError({"plant": _("Il sito di un gruppo non si può cambiare.")})
    extra = {}
    headcount = serializer.validated_data.get("headcount")
    if headcount is not None and headcount != audience.headcount:
        extra["headcount_updated_at"] = timezone.localdate()
    audience = serializer.save(**extra)
    _audit(user, "audience.update", audience, {"headcount": audience.headcount})
    return audience


def delete_audience(audience, user):
    # Foglia: le erogazioni conservano i propri conteggi, quindi eliminare un
    # gruppo non altera lo storico.
    require_training_manage(user, audience.plant)
    audience.soft_delete()
    _audit(user, "audience.delete", audience, {})


# ── Piano formativo ─────────────────────────────────────────────────────────

def create_plan(serializer, user):
    require_training_manage(user, serializer.validated_data.get("plant"))
    plan = serializer.save(created_by=user)
    _audit(user, "plan.create", plan, {"year": plan.year})
    return plan


def update_plan(serializer, user):
    plan = serializer.instance
    require_training_manage(user, plan.plant)
    if "plant" in serializer.validated_data and serializer.validated_data["plant"] != plan.plant:
        raise ValidationError({"plant": _("Il sito di un piano non si può cambiare.")})
    plan = serializer.save()
    _audit(user, "plan.update", plan, {"year": plan.year})
    return plan


def delete_plan(plan, user):
    require_training_manage(user, plan.plant)
    if TrainingSession.objects.filter(plan_item__plan=plan).exists():
        raise ValidationError(
            _("Il piano ha erogazioni registrate: non si può eliminare.")
        )
    with transaction.atomic():
        for item in plan.items.all():
            item.soft_delete()
        plan.soft_delete()
    _audit(user, "plan.delete", plan, {})


def _check_audiences(audiences, plant):
    """I gruppi devono essere del sito (piano/erogazione di sito); per un piano
    di organizzazione (`plant=None`) valgono i gruppi di qualunque sito."""
    if plant is None:
        return
    wrong = [a for a in audiences if a.plant_id != plant.pk]
    if wrong:
        raise ValidationError({"audiences": _("I gruppi devono appartenere allo stesso sito.")})


def create_plan_item(serializer, user):
    plan = serializer.validated_data["plan"]
    require_training_manage(user, plan.plant)
    _check_audiences(serializer.validated_data.get("audiences", []), plan.plant)
    item = serializer.save(created_by=user)
    _audit(user, "plan_item.create", item, {"plan_id": str(plan.pk)})
    return item


def update_plan_item(serializer, user):
    item = serializer.instance
    require_training_manage(user, item.plan.plant)
    if "plan" in serializer.validated_data and serializer.validated_data["plan"] != item.plan:
        raise ValidationError({"plan": _("Una voce non si può spostare in un altro piano.")})
    _check_audiences(serializer.validated_data.get("audiences", []), item.plan.plant)
    item = serializer.save()
    _audit(user, "plan_item.update", item, {"plan_id": str(item.plan_id)})
    return item


def delete_plan_item(item, user):
    require_training_manage(user, item.plan.plant)
    if item.sessions.exists():
        raise ValidationError(
            _("La voce ha erogazioni registrate: non si può eliminare.")
        )
    item.soft_delete()
    _audit(user, "plan_item.delete", item, {"plan_id": str(item.plan_id)})


def item_state(item, today=None) -> str:
    """fatto / in_ritardo / in_scadenza / pianificato. Si basa sulle erogazioni
    collegate (`has_sessions` annotato, altrimenti query)."""
    today = today or timezone.localdate()
    done = getattr(item, "has_sessions", None)
    if done is None:
        done = item.sessions.exists()
    if done:
        return "fatto"
    if item.due_date < today:
        return "in_ritardo"
    if item.due_date <= today + timedelta(days=DUE_SOON_DAYS):
        return "in_scadenza"
    return "pianificato"


def plan_status(plan, today=None) -> dict:
    """Stato del piano voce per voce, con la copertura per le voci che hanno
    gruppi di destinatari (formati ≤ destinatari, per non superare il 100%)."""
    today = today or timezone.localdate()
    items = list(
        plan.items.select_related("course")
        .prefetch_related("audiences", "sessions")
        .order_by("due_date")
    )
    rows = []
    counts = {"fatto": 0, "in_ritardo": 0, "in_scadenza": 0, "pianificato": 0}
    for item in items:
        sessions = list(item.sessions.all())
        item.has_sessions = bool(sessions)
        state = item_state(item, today)
        counts[state] += 1
        target = sum(a.headcount for a in item.audiences.all()) or None
        trained = sum(s.trained_count or 0 for s in sessions)
        rows.append({
            "item_id": str(item.pk),
            "course_id": str(item.course_id),
            "course_title": item.course.title,
            "due_date": item.due_date,
            "state": state,
            "sessions": len(sessions),
            "target_count": target,
            "trained_count": trained,
            "coverage_pct": round(min(trained, target) / target * 100, 1) if target else None,
        })
    return {"plan_id": str(plan.pk), "year": plan.year, "counts": counts, "items": rows}


# ── Erogazioni ──────────────────────────────────────────────────────────────

def _validate_counts(kind, data):
    if kind == "phishing":
        sent = data.get("sent_count")
        if sent is None:
            raise ValidationError({"sent_count": _("Indica quante e-mail sono state inviate.")})
        clicked = data.get("clicked_count") or 0
        reported = data.get("reported_count") or 0
        if clicked + reported > sent:
            raise ValidationError(
                {"clicked_count": _("Clic e segnalazioni non possono superare le e-mail inviate.")}
            )
        return
    target, trained = data.get("target_count"), data.get("trained_count")
    if target is None:
        raise ValidationError(
            {"target_count": _("Indica quante persone andavano formate o scegli i gruppi.")}
        )
    if trained is None:
        raise ValidationError({"trained_count": _("Indica quante persone sono state formate.")})
    if trained > target:
        raise ValidationError(
            {"trained_count": _("Le persone formate non possono superare quelle da formare.")}
        )


def _match_plan_item(course, plant, held_on):
    """Voce del piano dell'anno (del sito, poi di organizzazione) per lo stesso
    corso: la prima ancora senza erogazioni, altrimenti la più vicina."""
    base = TrainingPlanItem.objects.filter(
        course=course, plan__year=held_on.year, plan__deleted_at__isnull=True,
    ).annotate(
        has_sessions=Exists(TrainingSession.objects.filter(plan_item=OuterRef("pk")))
    )
    for scope in (Q(plan__plant=plant), Q(plan__plant__isnull=True)):
        items = list(base.filter(scope).order_by("due_date"))
        if items:
            open_items = [i for i in items if not i.has_sessions]
            return (open_items or items)[0]
    return None


def _evidence_valid_until(course, held_on):
    if not course.validity_months:
        return None
    return held_on + relativedelta(months=course.validity_months)


def _check_plan_item(plan_item, course, plant):
    if plan_item.course_id != course.pk:
        raise ValidationError({"plan_item": _("La voce del piano riguarda un altro corso.")})
    if plan_item.plan.plant_id not in (None, plant.pk):
        raise ValidationError({"plan_item": _("La voce del piano è di un altro sito.")})


def register_session(serializer, uploaded_file, user):
    """Registra un'erogazione con il file di prova, da cui nasce l'evidenza."""
    from apps.documents.services import create_evidence_with_file

    data = serializer.validated_data
    data.pop("file", None)
    course, plant = data["course"], data.get("plant")
    if plant is None:
        raise ValidationError({"plant": _("Indica il sito dell'erogazione.")})
    require_training_manage(user, plant)
    if course.status != "attivo":
        raise ValidationError({"course": _("Il corso è archiviato.")})
    if not uploaded_file:
        raise ValidationError(
            {"file": _("Allega la prova dell'erogazione (registro presenze, export, report).")}
        )
    held_on = data["held_on"]
    if held_on > timezone.localdate():
        raise ValidationError({"held_on": _("La data dell'erogazione non può essere futura.")})

    audiences = data.get("audiences", [])
    _check_audiences(audiences, plant)
    if course.kind != "phishing" and data.get("target_count") is None and audiences:
        data["target_count"] = sum(a.headcount for a in audiences)
    _validate_counts(course.kind, data)

    plan_item = data.get("plan_item")
    if plan_item is not None:
        _check_plan_item(plan_item, course, plant)
    else:
        data["plan_item"] = _match_plan_item(course, plant, held_on)

    valid_until = _evidence_valid_until(course, held_on)
    with transaction.atomic():
        evidence = create_evidence_with_file(
            {
                "title": f"{course.title} — {held_on.isoformat()}",
                "evidence_type": "certificato" if course.kind == "corso" else "report",
                "valid_until": valid_until.isoformat() if valid_until else "",
                "plant": str(plant.pk),
            },
            uploaded_file,
            user,
        )
        session = serializer.save(created_by=user, evidence=evidence, legacy=False)
    _audit(user, "session.register", session, {
        "course_id": str(course.pk),
        "plant_id": str(plant.pk),
        "evidence_id": str(evidence.pk),
        "target_count": session.target_count,
        "trained_count": session.trained_count,
        "sent_count": session.sent_count,
    })
    return session


_IMMUTABLE_SESSION_FIELDS = ("course", "plant")


def update_session(serializer, user):
    session = serializer.instance
    require_training_manage(user, session.plant)
    data = serializer.validated_data
    data.pop("file", None)
    for f in _IMMUTABLE_SESSION_FIELDS:
        if f in data and data[f] != getattr(session, f):
            raise ValidationError({f: _("Campo non modificabile: elimina e registra di nuovo.")})
    held_on = data.get("held_on", session.held_on)
    if held_on > timezone.localdate():
        raise ValidationError({"held_on": _("La data dell'erogazione non può essere futura.")})
    if "audiences" in data and session.plant is not None:
        _check_audiences(data["audiences"], session.plant)
    merged = {
        f: data.get(f, getattr(session, f))
        for f in ("target_count", "trained_count", "sent_count", "clicked_count", "reported_count")
    }
    _validate_counts(session.course.kind, merged)
    if data.get("plan_item") is not None and session.plant is not None:
        _check_plan_item(data["plan_item"], session.course, session.plant)

    with transaction.atomic():
        session = serializer.save()
        if session.evidence_id and "held_on" in data:
            ev = session.evidence
            ev.valid_until = _evidence_valid_until(session.course, session.held_on)
            ev.save(update_fields=["valid_until", "updated_at"])
    _audit(user, "session.update", session, {
        "target_count": session.target_count,
        "trained_count": session.trained_count,
        "sent_count": session.sent_count,
    })
    return session


def delete_session(session, user):
    """Soft delete dell'erogazione e della sua evidenza. Come per ogni evidenza,
    non si cancella se prova controlli già valutati (salvo superuser)."""
    from django.core.exceptions import ValidationError as DjangoValidationError

    from apps.documents.services import delete_evidence

    require_training_manage(user, session.plant)
    with transaction.atomic():
        if session.evidence_id and session.evidence.deleted_at is None:
            try:
                delete_evidence(session.evidence, user)
            except DjangoValidationError as e:
                raise ValidationError({"detail": e.messages[0]}) from e
        session.soft_delete()
    _audit(user, "session.delete", session, {"course_id": str(session.course_id)})

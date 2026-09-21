from datetime import timedelta

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.exceptions import PermissionDenied, ValidationError

from core.audit import log_action

from .models import (
    TrainingAudience,
    TrainingParticipant,
    TrainingPlanItem,
    TrainingSession,
)

# Chi gestisce piano, gruppi ed erogazioni: questi ruoli GRC oppure chi ha la
# nomina di CISO in Governance. Nessuna assegnazione: registra chi arriva prima.
MANAGER_ROLES = frozenset({"super_admin", "compliance_officer", "plant_manager"})
# Piani, gruppi ed erogazioni sono conteggi e file di prova, non dati personali:
# li leggono anche gli auditor, interni ed esterni (sono l'evidenza che cercano).
RECORD_READ_ROLES = MANAGER_ROLES | {"internal_auditor", "external_auditor"}
DUE_SOON_DAYS = 30
# Indicatori: finestra delle campagne di phishing considerate, anticipo con cui
# segnalare una prova in scadenza, età oltre cui un headcount va riverificato.
PHISHING_WINDOW_DAYS = 365
EVIDENCE_EXPIRING_DAYS = 60
HEADCOUNT_STALE_MONTHS = 6
# Promemoria delle voci del piano: task M08 riconoscibili per la deduplica.
REMINDER_SOURCE_MODULE = "M15"
OPEN_TASK_STATUSES = ("aperto", "in_corso", "scaduto")


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


def _manage_scopes(user):
    """Perimetri su cui `user` gestisce la formazione: (org, bu_ids, plant_ids).
    Ruoli GRC di gestione per il loro perimetro più le nomine CISO attive."""
    from apps.auth_grc.models import UserPlantAccess

    org, bu_ids, plant_ids = False, set(), set()
    for access in UserPlantAccess.objects.filter(
        user=user, role__in=MANAGER_ROLES, deleted_at__isnull=True,
    ).prefetch_related("scope_plants"):
        if access.scope_type == "org":
            org = True
        elif access.scope_type == "bu" and access.scope_bu_id:
            bu_ids.add(access.scope_bu_id)
        elif access.scope_type in ("plant_list", "single_plant"):
            plant_ids.update(p.pk for p in access.scope_plants.all())
    for a in _active_ciso_assignments(user):
        if a.scope_type == "org":
            org = True
        elif a.scope_type == "bu" and a.scope_id:
            bu_ids.add(a.scope_id)
        elif a.scope_type == "plant" and a.scope_id:
            plant_ids.add(a.scope_id)
    return org, bu_ids, plant_ids


def _in_scopes(scopes, plant) -> bool:
    org, bu_ids, plant_ids = scopes
    if org:
        return True
    if plant is None:
        return False
    return plant.pk in plant_ids or bool(plant.bu_id and plant.bu_id in bu_ids)


def can_manage_training(user, plant) -> bool:
    """True se `user` gestisce la formazione del sito (`plant=None` = piano di
    organizzazione, che richiede un perimetro di organizzazione)."""
    if getattr(user, "is_superuser", False):
        return True
    return _in_scopes(_manage_scopes(user), plant)


def training_capabilities(user) -> dict:
    """Cosa può fare l'utente nel modulo, per l'interfaccia: leggere piani ed
    erogazioni, gestire la formazione di organizzazione, su quali siti. Il
    backend ricontrolla comunque ogni scrittura."""
    from apps.plants.models import Plant
    from core.permissions import user_has_any_role
    from core.scoping import scope_queryset_by_plant

    manager = is_training_manager(user)
    plants = scope_queryset_by_plant(Plant.objects.all(), user, plant_field="pk").only("id", "bu_id")
    if getattr(user, "is_superuser", False):
        manage_org, manage_ids = True, [str(p.pk) for p in plants]
    else:
        scopes = _manage_scopes(user)
        manage_org = scopes[0]
        manage_ids = [str(p.pk) for p in plants if _in_scopes(scopes, p)]
    return {
        "can_read_records": manager or user_has_any_role(user, RECORD_READ_ROLES),
        "can_manage_courses": manager,
        "can_manage_org": manage_org,
        "manage_plant_ids": manage_ids,
    }


def competency_options() -> list[str]:
    from apps.auth_grc.models import RoleCompetencyRequirement

    return sorted(set(
        RoleCompetencyRequirement.objects.values_list("competency", flat=True)
    ), key=str.lower)


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


# ── Catalogo corsi ──────────────────────────────────────────────────────────

def delete_course(course, user):
    """Un corso già in un piano o con erogazioni non si elimina: le voci e le
    prove resterebbero senza corso. Si archivia."""
    if course.plan_items.exists() or course.sessions.exists():
        raise ValidationError(
            _("Il corso è in un piano formativo o ha erogazioni registrate: archivialo.")
        )
    course.soft_delete()
    _audit(user, "course.delete", course, {})


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


# ── Indicatori (KPI, Reporting, Cockpit) ───────────────────────────────────
# Solo conteggi per corso, sito e gruppo: nessun dato personale (regola #11).

def _items_in_scope(plant):
    """Voci dei piani del sito più quelle del piano di organizzazione, che vale
    per ogni sito (`plant=None` = tutti i piani)."""
    qs = TrainingPlanItem.objects.filter(plan__deleted_at__isnull=True)
    if plant is not None:
        qs = qs.filter(Q(plan__plant=plant) | Q(plan__plant__isnull=True))
    return qs


def session_valid_on(session, day) -> bool:
    """Un'erogazione vale fino a `held_on + validity_months` del corso."""
    months = session.course.validity_months
    return months is None or session.held_on + relativedelta(months=months) >= day


def training_coverage(plant=None, today=None) -> dict:
    """Copertura della formazione obbligatoria del personale generale.

    Per ogni corso obbligatorio del piano dell'anno e per ogni sito: persone da
    formare = somma degli headcount dei gruppi destinatari delle sue voci;
    formate = persone formate nelle erogazioni ancora valide del corso su quel
    sito, fino al massimo delle persone da formare. Le voci senza gruppi non
    hanno un denominatore e restano fuori; le erogazioni storiche migrate
    (`legacy`) pure, perché contavano gli utenti della piattaforma e non il
    personale.
    """
    today = today or timezone.localdate()
    items = (
        _items_in_scope(plant)
        .filter(
            plan__year=today.year, course__status="attivo", course__mandatory=True,
            course__audience_kind="generale",
        )
        .exclude(course__kind="phishing")
        .select_related("course")
        .prefetch_related("audiences__plant")
    )
    targets, courses, plants = {}, {}, {}
    for item in items:
        courses[item.course_id] = item.course
        for aud in item.audiences.all():
            if plant is not None and aud.plant_id != plant.pk:
                continue
            plants[aud.plant_id] = aud.plant
            targets.setdefault((item.course_id, aud.plant_id), {})[aud.pk] = aud.headcount

    trained = {}
    if targets:
        sessions = TrainingSession.objects.filter(
            course_id__in=list(courses), plant_id__in=list(plants),
            legacy=False, held_on__lte=today,
        ).select_related("course")
        for s in sessions:
            if session_valid_on(s, today):
                key = (s.course_id, s.plant_id)
                trained[key] = trained.get(key, 0) + (s.trained_count or 0)

    rows, total_target, total_covered = [], 0, 0
    for (course_id, plant_id), audiences in targets.items():
        target = sum(audiences.values())
        done = trained.get((course_id, plant_id), 0)
        covered = min(done, target)
        total_target += target
        total_covered += covered
        rows.append({
            "course_id": str(course_id),
            "course_title": courses[course_id].title,
            "plant_id": str(plant_id),
            "plant_code": plants[plant_id].code,
            "target": target,
            "trained": done,
            "pct": round(covered / target * 100, 1) if target else None,
        })
    rows.sort(key=lambda r: (r["pct"] if r["pct"] is not None else 101, r["course_title"]))
    return {
        "year": today.year,
        "target": total_target,
        "covered": total_covered,
        "pct": round(total_covered / total_target * 100, 1) if total_target else None,
        "rows": rows,
    }


def plan_progress(plant=None, today=None) -> dict:
    """Avanzamento del piano dell'anno: voci già scadute con almeno
    un'erogazione su voci già scadute; più le voci in ritardo di qualunque
    anno e quelle in scadenza entro DUE_SOON_DAYS. Come nel resto del modulo,
    una voce del piano di organizzazione è fatta quando ha un'erogazione."""
    today = today or timezone.localdate()
    items = _items_in_scope(plant).filter(course__status="attivo").annotate(
        has_sessions=Exists(TrainingSession.objects.filter(plan_item=OuterRef("pk"))),
    )
    due = items.filter(plan__year=today.year, due_date__lt=today)
    due_n = due.count()
    done_n = due.filter(has_sessions=True).count()
    return {
        "year": today.year,
        "items": items.filter(plan__year=today.year).count(),
        "due": due_n,
        "done": done_n,
        "pct": round(done_n / due_n * 100, 1) if due_n else None,
        "overdue": items.filter(has_sessions=False, due_date__lt=today).count(),
        "due_soon": items.filter(
            has_sessions=False, due_date__gte=today,
            due_date__lte=today + timedelta(days=DUE_SOON_DAYS),
        ).count(),
    }


def latest_phishing(plant=None, today=None) -> dict:
    """Ultima campagna di phishing di ogni sito negli ultimi
    PHISHING_WINDOW_DAYS giorni, con i tassi di clic e di segnalazione sul
    totale delle e-mail inviate. Le campagne storiche migrate valgono: i loro
    conteggi vengono dagli esiti reali."""
    today = today or timezone.localdate()
    qs = TrainingSession.objects.filter(
        course__kind="phishing", sent_count__gt=0,
        held_on__gte=today - timedelta(days=PHISHING_WINDOW_DAYS), held_on__lte=today,
    ).select_related("course", "plant").order_by("-held_on", "-created_at")
    if plant is not None:
        qs = qs.filter(plant=plant)
    latest = {}
    for s in qs:
        latest.setdefault(s.plant_id, s)
    campaigns = sorted(latest.values(), key=lambda s: s.held_on, reverse=True)
    sent = sum(s.sent_count for s in campaigns)
    clicked = sum(s.clicked_count or 0 for s in campaigns)
    reported = sum(s.reported_count or 0 for s in campaigns)
    return {
        "sent": sent,
        "clicked": clicked,
        "reported": reported,
        "click_pct": round(clicked / sent * 100, 1) if sent else None,
        "report_pct": round(reported / sent * 100, 1) if sent else None,
        "campaigns": [{
            "session_id": str(s.pk),
            "course_title": s.course.title,
            "plant_code": s.plant.code if s.plant_id else None,
            "held_on": s.held_on,
            "sent": s.sent_count,
            "clicked": s.clicked_count or 0,
            "reported": s.reported_count or 0,
            "legacy": s.legacy,
        } for s in campaigns],
    }


def expiring_training_evidence(plant=None, today=None) -> list:
    """Per ogni corso e sito, l'erogazione più recente la cui prova è già
    scaduta o scade entro EVIDENCE_EXPIRING_DAYS: va ripetuta. Un'erogazione
    più vecchia già sostituita da una nuova non viene segnalata."""
    today = today or timezone.localdate()
    qs = TrainingSession.objects.filter(
        legacy=False, evidence__isnull=False, evidence__deleted_at__isnull=True,
        course__status="attivo",
    ).select_related("course", "plant", "evidence").order_by("-held_on", "-created_at")
    if plant is not None:
        qs = qs.filter(plant=plant)
    latest = {}
    for s in qs:
        latest.setdefault((s.course_id, s.plant_id), s)
    limit = today + timedelta(days=EVIDENCE_EXPIRING_DAYS)
    rows = [{
        "session_id": str(s.pk),
        "course_title": s.course.title,
        "plant_code": s.plant.code if s.plant_id else None,
        "held_on": s.held_on,
        "valid_until": s.evidence.valid_until,
        "expired": s.evidence.valid_until < today,
    } for s in latest.values() if s.evidence.valid_until and s.evidence.valid_until <= limit]
    return sorted(rows, key=lambda r: r["valid_until"])


def board_training(plant=None, today=None) -> dict:
    """Formazione dell'organo di gestione (NIS2 art. 20): componenti in carica
    degli organi di tipo CdA del perimetro con un'erogazione ancora valida di
    un corso per l'organo di gestione. Un organo senza siti governa l'intera
    organizzazione e vale per ogni sito. Un componente con account è
    riconosciuto anche se è stato scelto fra i titolari di nomine."""
    from apps.governance.models import CommitteeMember

    today = today or timezone.localdate()
    members = _active_on(
        CommitteeMember.objects.filter(
            committee__committee_type="cda", committee__deleted_at__isnull=True,
        ),
        today,
    ).select_related("committee")
    if plant is not None:
        members = members.filter(
            Q(committee__plants=plant) | Q(committee__plants__isnull=True),
        ).distinct()
    members = list(members.order_by("committee__name", "full_name"))

    user_ids = {m.user_id for m in members if m.user_id}
    participations = TrainingParticipant.objects.filter(
        session__deleted_at__isnull=True, session__legacy=False,
        session__held_on__lte=today, session__course__audience_kind="organo_gestione",
    ).filter(
        Q(committee_member__in=[m.pk for m in members]) | Q(user_id__in=user_ids),
    ).select_related("session__course")
    # Scadenza più lontana fra le erogazioni valide di ciascuno (None = non scade).
    best_member, best_user = {}, {}
    for p in participations:
        if not session_valid_on(p.session, today):
            continue
        until = _evidence_valid_until(p.session.course, p.session.held_on)
        for key, best in ((p.committee_member_id, best_member), (p.user_id, best_user)):
            if key is None:
                continue
            if key not in best or (best[key] is not None and (until is None or until > best[key])):
                best[key] = until

    rows, trained = [], 0
    for m in members:
        found = [b[k] for b, k in ((best_member, m.pk), (best_user, m.user_id)) if k in b]
        ok = bool(found)
        trained += ok
        valid_until = None if not ok or None in found else max(found)
        rows.append({
            "member_id": str(m.pk),
            "full_name": m.full_name,
            "position": m.position,
            "committee": m.committee.name,
            "trained": ok,
            "valid_until": valid_until,
        })
    total = len(members)
    return {
        "total": total,
        "trained": trained,
        "pct": round(trained / total * 100, 1) if total else None,
        "members": rows,
    }


def stale_audiences_count(plant=None, today=None) -> int:
    """Gruppi il cui headcount non viene riverificato da più di
    HEADCOUNT_STALE_MONTHS mesi: la copertura si calcola su numeri vecchi."""
    today = today or timezone.localdate()
    qs = TrainingAudience.objects.filter(
        headcount_updated_at__lt=today - relativedelta(months=HEADCOUNT_STALE_MONTHS),
    )
    if plant is not None:
        qs = qs.filter(plant=plant)
    return qs.count()


# ── Promemoria delle voci del piano ────────────────────────────────────────

def _reminder_text(item, state, today):
    plan = item.plan
    scope = plan.plant.name if plan.plant_id else "organizzazione"
    headcount = sum(a.headcount for a in item.audiences.all())
    lines = [
        f"Piano formativo {plan.year} ({scope}): «{item.course.title}».",
        f"Scadenza della voce: {item.due_date.isoformat()}"
        + (f" ({(today - item.due_date).days} giorni fa)." if state == "in_ritardo"
           else f" (fra {(item.due_date - today).days} giorni)."),
    ]
    if headcount:
        lines.append(f"Destinatari previsti: {headcount} persone.")
    lines.append(
        "Registra l'erogazione in Formazione allegando la prova (registro presenze, "
        "export e-learning, report della campagna): il promemoria si chiude da solo."
    )
    return "\n".join(lines)


def remind_plan_items(today=None) -> dict:
    """Per ogni voce del piano senza erogazioni, in scadenza entro
    DUE_SOON_DAYS o già in ritardo, apre un task al compliance officer del
    perimetro (regola #7) e avvisa via M19 chi segue la formazione.

    Un solo promemoria per voce: se ne esiste già uno non chiuso (o annullato
    da chi lo ha ricevuto) non se ne apre un altro. Ritorna solo conteggi.
    """
    from apps.auth_grc.models import GrcRole
    from apps.notifications.resolver import fire_notification
    from apps.plants.services import plant_today
    from apps.tasks.models import Task
    from apps.tasks.services import create_task

    horizon = (today or timezone.localdate()) + timedelta(days=DUE_SOON_DAYS + 1)
    reminded = Task.objects.filter(
        source_module=REMINDER_SOURCE_MODULE, source_id=OuterRef("pk"),
        status__in=OPEN_TASK_STATUSES + ("annullato",),
    )
    items = (
        TrainingPlanItem.objects.filter(
            plan__deleted_at__isnull=True, course__status="attivo", due_date__lte=horizon,
        )
        .annotate(
            has_sessions=Exists(TrainingSession.objects.filter(plan_item=OuterRef("pk"))),
            reminded=Exists(reminded),
        )
        .filter(has_sessions=False, reminded=False)
        .select_related("plan__plant", "course")
        .prefetch_related("audiences")
    )
    counts = {"in_scadenza": 0, "in_ritardo": 0}
    for item in items:
        day = today or plant_today(item.plan.plant)
        state = item_state(item, day)
        if state not in counts:
            continue
        late = state == "in_ritardo"
        create_task(
            plant=item.plan.plant,
            title=f"Formazione {'in ritardo' if late else 'in scadenza'}: {item.course.title}",
            description=_reminder_text(item, state, day),
            priority="alta" if late else "media",
            source_module=REMINDER_SOURCE_MODULE,
            source_id=item.pk,
            due_date=day + timedelta(days=7) if late else item.due_date,
            assign_type="role",
            assign_value=GrcRole.COMPLIANCE_OFFICER,
        )
        fire_notification(
            "training_plan_due",
            plant=item.plan.plant,
            context={"item": item, "state": state, "today": day},
        )
        counts[state] += 1
    return counts


# ── Partecipanti nominativi (ruoli critici, organo di gestione) ─────────────

def _active_on(qs, day):
    """Nomine e componenti in carica il giorno `day`."""
    return qs.filter(valid_from__lte=day).filter(
        Q(valid_until__isnull=True) | Q(valid_until__gte=day),
    )


def _covers(assignment, plant) -> bool:
    if assignment.scope_type == "org":
        return True
    if assignment.scope_type == "bu":
        return bool(plant.bu_id) and assignment.scope_id == plant.bu_id
    return assignment.scope_id == plant.pk


def _person_name(user) -> str:
    return user.get_full_name().strip() or user.email or user.username


def participant_options(plant, day) -> dict:
    """Chi può partecipare a un'erogazione nominativa del sito alla data `day`:
    i titolari di nomine attive che coprono il sito e i componenti in carica
    degli organi di governo del sito (o di organizzazione)."""
    from apps.governance.models import CommitteeMember, RoleAssignment

    holders = {}
    assignments = _active_on(
        RoleAssignment.objects.filter(user__is_active=True), day,
    ).select_related("user").order_by("role")
    for a in assignments:
        if not _covers(a, plant):
            continue
        entry = holders.setdefault(a.user_id, {
            "user_id": str(a.user_id), "name": _person_name(a.user), "roles": [],
        })
        if a.role not in entry["roles"]:
            entry["roles"].append(a.role)

    members = _active_on(
        CommitteeMember.objects.filter(committee__deleted_at__isnull=True), day,
    ).filter(
        Q(committee__plants=plant) | Q(committee__plants__isnull=True),
    ).distinct().select_related("committee").order_by("committee__name", "full_name")
    return {
        "role_holders": sorted(holders.values(), key=lambda h: h["name"].lower()),
        "members": [{
            "member_id": str(m.pk),
            "name": m.full_name,
            "position": m.position,
            "committee": m.committee.name,
            "management_body": m.committee.is_management_body,
            "user_id": str(m.user_id) if m.user_id else None,
        } for m in members],
    }


def _resolve_participants(plant, held_on, users, members) -> list[dict]:
    """Valida i partecipanti scelti contro le opzioni del sito alla data
    dell'erogazione e li unifica: chi è sia componente di un organo sia
    titolare di nomine diventa un solo partecipante."""
    options = participant_options(plant, held_on)
    holders = {h["user_id"]: h for h in options["role_holders"]}
    allowed_members = {m["member_id"] for m in options["members"]}
    if any(str(u.pk) not in holders for u in users):
        raise ValidationError({"participant_users": _(
            "Si possono scegliere solo titolari di nomine attive su questo sito alla data dell'erogazione."
        )})
    if any(str(m.pk) not in allowed_members for m in members):
        raise ValidationError({"participant_members": _(
            "Si possono scegliere solo componenti in carica degli organi di governo di questo sito."
        )})
    if not users and not members:
        raise ValidationError({"participant_users": _(
            "Indica chi ha partecipato: titolari di nomine o componenti degli organi di governo."
        )})

    people, by_user = [], {}
    for m in members:
        entry = {"user": m.user, "committee_member": m, "roles": []}
        people.append(entry)
        if m.user_id:
            by_user[m.user_id] = entry
    for u in users:
        entry = by_user.get(u.pk)
        if entry is None:
            entry = {"user": u, "committee_member": None, "roles": []}
            people.append(entry)
            by_user[u.pk] = entry
        entry["roles"] = holders[str(u.pk)]["roles"]
    # Un componente con account che è anche titolare di nomine porta le sue
    # nomine anche se è stato scelto solo come componente.
    for entry in people:
        user = entry["user"]
        if user is not None and not entry["roles"] and str(user.pk) in holders:
            entry["roles"] = holders[str(user.pk)]["roles"]
    return people


_COMPETENCY_FIELDS = ("level", "evidence_id", "evidence_type", "obtained_at", "valid_until",
                      "certification_body", "verified_by_id")


def _competency_snapshot(uc) -> dict:
    snap = {f: getattr(uc, f) for f in _COMPETENCY_FIELDS}
    for f in ("evidence_id", "verified_by_id"):
        snap[f] = str(snap[f]) if snap[f] else None
    for f in ("obtained_at", "valid_until"):
        snap[f] = snap[f].isoformat() if snap[f] else None
    return snap


def _restore_snapshot(uc, snap):
    from datetime import date

    for f in _COMPETENCY_FIELDS:
        value = snap.get(f)
        if f in ("obtained_at", "valid_until") and value:
            value = date.fromisoformat(value)
        setattr(uc, f, value)
    uc.save()


def _apply_competency(participant, course, session, user):
    """ISO 27001 cl. 7.2: l'erogazione aggiorna la competenza del partecipante
    con account. Non abbassa un livello più alto già posseduto e non
    sostituisce una prova più recente dello stesso livello."""
    from apps.auth_grc.models import UserCompetency

    if not course.competency or participant.user_id is None:
        return
    level = course.competency_level
    uc = UserCompetency.objects.filter(
        user_id=participant.user_id, competency=course.competency,
    ).first()
    if uc is not None and (
        uc.level > level
        or (uc.level == level and uc.obtained_at and uc.obtained_at > session.held_on)
    ):
        return
    before = _competency_snapshot(uc) if uc is not None else None
    if uc is None:
        uc = UserCompetency(
            user_id=participant.user_id, competency=course.competency, created_by=user,
        )
    uc.level = level
    uc.evidence = session.evidence
    uc.evidence_type = "training"
    uc.obtained_at = session.held_on
    uc.valid_until = session.evidence.valid_until if session.evidence_id else None
    uc.certification_body = ""
    uc.verified_by = user
    uc.save()
    participant.competency = uc
    participant.competency_before = before
    participant.save(update_fields=["competency", "competency_before", "updated_at"])


def _revert_competencies(session):
    """Eliminata l'erogazione, le competenze che essa sosteneva tornano allo
    stato precedente. Se quello stato veniva a sua volta da un'erogazione già
    eliminata si risale ancora; se la competenza era nata dall'erogazione, la
    si elimina (soft). Una competenza aggiornata poi da altro resta com'è."""
    for p in session.participants.filter(competency__isnull=False).select_related("competency"):
        uc = p.competency
        if uc.deleted_at is not None or uc.evidence_id != session.evidence_id:
            continue
        snap = p.competency_before
        for _step in range(50):
            if not snap or not snap.get("evidence_id"):
                break
            prev = TrainingParticipant.objects.filter(
                competency=uc, session__evidence_id=snap["evidence_id"],
                session__deleted_at__isnull=False,
            ).first()
            if prev is None:
                break
            snap = prev.competency_before
        if snap is None:
            uc.soft_delete()
        else:
            _restore_snapshot(uc, snap)


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


def link_evidence_to_controls(evidence, course, plant) -> dict:
    """Collega l'evidenza dell'erogazione alle istanze dei controlli del corso
    sul sito. Un controllo non istanziato sul sito, o escluso dallo SOA, non è
    un errore: lo si segnala come non applicabile."""
    from apps.controls.models import ControlInstance

    controls = list(course.controls.all().only("id", "external_id"))
    if not controls:
        return {"linked": 0, "not_applicable": []}
    instances = list(
        ControlInstance.objects.filter(
            plant=plant, control__in=controls, deleted_at__isnull=True,
        ).exclude(applicability__in=("escluso", "non_pertinente")).only("id", "control_id")
    )
    if instances:
        evidence.control_instances.add(*instances)
        # L'aggiunta dal lato dell'evidenza non tocca le istanze: le si segna
        # aggiornate come fa il segnale di controls per il collegamento manuale.
        ControlInstance.objects.filter(pk__in=[i.pk for i in instances]).update(
            updated_at=timezone.now(),
        )
    covered = {i.control_id for i in instances}
    return {
        "linked": len(instances),
        "not_applicable": sorted(c.external_id for c in controls if c.pk not in covered),
    }


def _close_plan_item_reminders(plan_item, user):
    """Registrata l'erogazione, il promemoria della voce del piano non serve più."""
    from apps.tasks.models import Task
    from apps.tasks.services import complete_task

    for task in Task.objects.filter(
        source_module=REMINDER_SOURCE_MODULE, source_id=plan_item.pk,
        status__in=OPEN_TASK_STATUSES,
    ):
        complete_task(task, user, notes=_("Erogazione registrata."))


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
    users = data.pop("participant_users", [])
    members = data.pop("participant_members", [])
    people = []
    if course.is_named:
        # Ruoli critici e organo di gestione: si registra chi ha partecipato,
        # i conteggi ne derivano.
        if audiences:
            raise ValidationError({"audiences": _(
                "Per questo corso si indicano i partecipanti, non i gruppi di destinatari."
            )})
        people = _resolve_participants(plant, held_on, users, members)
        data["trained_count"] = len(people)
        if data.get("target_count") is None:
            data["target_count"] = len(people)
    elif users or members:
        raise ValidationError({"participant_users": _(
            "Le erogazioni per il personale registrano solo conteggi, non nominativi."
        )})
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
        for person in people:
            participant = TrainingParticipant.objects.create(
                session=session, user=person["user"],
                committee_member=person["committee_member"], roles=person["roles"],
                created_by=user,
            )
            _apply_competency(participant, course, session, user)
        links = link_evidence_to_controls(evidence, course, plant)
        if session.plan_item_id:
            _close_plan_item_reminders(session.plan_item, user)
    session.control_links = links
    _audit(user, "session.register", session, {
        "course_id": str(course.pk),
        "plant_id": str(plant.pk),
        "evidence_id": str(evidence.pk),
        "target_count": session.target_count,
        "trained_count": session.trained_count,
        "sent_count": session.sent_count,
        "controls_linked": links["linked"],
        "controls_not_applicable": len(links["not_applicable"]),
        "participants": len(people),
    })
    return session


_IMMUTABLE_SESSION_FIELDS = ("course", "plant")


def update_session(serializer, user):
    session = serializer.instance
    require_training_manage(user, session.plant)
    data = serializer.validated_data
    data.pop("file", None)
    if "participant_users" in data or "participant_members" in data:
        raise ValidationError({"participant_users": _(
            "I partecipanti non si modificano: elimina l'erogazione e registrala di nuovo."
        )})
    if session.course.is_named and "trained_count" in data \
            and data["trained_count"] != session.participants.count():
        raise ValidationError({"trained_count": _(
            "Per questo corso le persone formate sono i partecipanti registrati."
        )})
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
            # Le competenze che poggiano su questa prova seguono la nuova data.
            from apps.auth_grc.models import UserCompetency
            UserCompetency.objects.filter(evidence=ev).update(
                obtained_at=session.held_on, valid_until=ev.valid_until, updated_at=timezone.now(),
            )
        if data.get("plan_item") is not None:
            _close_plan_item_reminders(session.plan_item, user)
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
        _revert_competencies(session)
    _audit(user, "session.delete", session, {"course_id": str(session.course_id)})

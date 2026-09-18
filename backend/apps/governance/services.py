from django.db.models import Q
from django.utils import timezone


def visible_role_assignments(qs, user):
    """Filtra le assegnazioni di ruolo visibili all'utente per perimetro plant.

    org-scope / superuser → tutto. Gli altri vedono le assegnazioni org-level
    (ruoli aziendali obbligatori, evidenza d'audit legittima) più quelle dei
    siti/BU a cui hanno accesso. Evita che un utente scoped a un sito (es.
    external_auditor) legga i titolari — con email/nome — di tutti gli altri
    siti.
    """
    from core.scoping import get_user_plant_ids
    from apps.plants.models import Plant

    allowed = get_user_plant_ids(user)
    if allowed is None:
        return qs  # org scope / superuser → nessun filtro
    allowed_bu_ids = set(
        Plant.objects.filter(id__in=allowed).values_list("bu_id", flat=True)
    )
    allowed_bu_ids.discard(None)
    return qs.filter(
        Q(scope_type="org")
        | Q(scope_type="plant", scope_id__in=allowed)
        | Q(scope_type="bu", scope_id__in=allowed_bu_ids)
    )


def get_active_role(user, role: str, scope_id=None):
    from .models import RoleAssignment

    today = timezone.localdate()
    qs = RoleAssignment.objects.filter(
        user=user,
        role=role,
        valid_from__lte=today,
        deleted_at__isnull=True,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today))
    if scope_id:
        qs = qs.filter(scope_id=scope_id)
    return qs.first()


def get_expiring_delegations(days: int = 90):
    from .models import RoleAssignment

    today = timezone.localdate()
    threshold = today + timezone.timedelta(days=days)
    return (
        RoleAssignment.objects.filter(
            valid_until__isnull=False,
            valid_until__lte=threshold,
            valid_until__gte=today,
            deleted_at__isnull=True,
        )
        .select_related("user")
    )


def terminate_role(assignment, user, termination_date=None, reason=""):
    """Termina un ruolo impostando valid_until."""
    from core.audit import log_action

    termination_date = termination_date or timezone.localdate()
    assignment.valid_until = termination_date
    assignment.notes = (
        f"{assignment.notes}\n[Terminato il {termination_date}: {reason}]"
    ).strip()
    assignment.save(update_fields=["valid_until", "notes", "updated_at"])

    log_action(
        user=user,
        action_code="governance.role.terminated",
        level="L1",
        entity=assignment,
        payload={
            "role":             assignment.role,
            "terminated_user":  str(assignment.user_id),
            "termination_date": str(termination_date),
            "reason":           (reason or "")[:200],
        },
    )
    return assignment


def replace_role(old_assignment, new_user, user,
                 handover_date=None, reason="", document_id=None):
    """Successione atomica: termina il vecchio ruolo e crea il nuovo."""
    from django.db import transaction
    from core.audit import log_action
    from .models import RoleAssignment

    handover_date = handover_date or timezone.localdate()

    already_holder = RoleAssignment.objects.filter(
        user=new_user,
        role=old_assignment.role,
        scope_type=old_assignment.scope_type,
        scope_id=old_assignment.scope_id,
        valid_until__isnull=True,
    ).exclude(pk=old_assignment.pk).exists()
    if already_holder:
        from django.core.exceptions import ValidationError
        from django.utils.translation import gettext_lazy as _

        raise ValidationError(_("Il nuovo titolare ha già questo ruolo attivo per questo perimetro."))

    with transaction.atomic():
        terminate_role(
            old_assignment, user,
            termination_date=handover_date,
            reason=reason or "Sostituzione ruolo",
        )

        new_assignment = RoleAssignment.objects.create(
            user=new_user,
            role=old_assignment.role,
            scope_type=old_assignment.scope_type,
            scope_id=old_assignment.scope_id,
            valid_from=handover_date,
            valid_until=None,
            framework_refs=old_assignment.framework_refs,
            document_id=document_id,
            notes=(
                f"Successore di "
                f"{old_assignment.user.get_full_name() or old_assignment.user.email}"
            ),
            created_by=user,
        )

        log_action(
            user=user,
            action_code="governance.role.replaced",
            level="L1",
            entity=new_assignment,
            payload={
                "role":          new_assignment.role,
                "old_user":      str(old_assignment.user_id),
                "new_user":      str(new_user.pk),
                "handover_date": str(handover_date),
                "reason":        (reason or "")[:200],
            },
        )

    return old_assignment, new_assignment


def get_expiring_roles(days=30):
    """Ruoli in scadenza nei prossimi N giorni o già scaduti."""
    from .models import RoleAssignment

    today     = timezone.localdate()
    threshold = today + timezone.timedelta(days=days)

    expiring = RoleAssignment.objects.filter(
        valid_until__isnull=False,
        valid_until__lte=threshold,
        valid_until__gte=today,
        deleted_at__isnull=True,
    ).select_related("user")

    expired = RoleAssignment.objects.filter(
        valid_until__isnull=False,
        valid_until__lt=today,
        deleted_at__isnull=True,
    ).select_related("user")

    return {"expiring": expiring, "expired": expired}


def _active_role_qs(role):
    """Assegnazioni attive (valide oggi, non eliminate) di un dato ruolo."""
    from .models import RoleAssignment

    today = timezone.localdate()
    return RoleAssignment.objects.filter(
        role=role,
        valid_from__lte=today,
        deleted_at__isnull=True,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today))


# Ruoli che per natura ammettono più titolari attivi sullo stesso perimetro,
# quando non esiste un RoleRequirement esplicito che ne fissi la policy.
DEFAULT_MULTI_HOLDER_ROLES = {
    "control_owner",
    "comitato_membro",
    "raci_responsible",
    "raci_accountable",
    "external_auditor",
}


def is_single_holder(role: str) -> bool:
    """True se il ruolo ammette un solo titolare attivo per perimetro.

    Configurabile per ruolo via ``RoleRequirement.single_holder``; in assenza di
    un requisito esplicito vale un default sensato (la maggior parte dei ruoli
    normativi è a titolare unico, tranne i ruoli distribuiti).
    """
    from .models import RoleRequirement

    req = (
        RoleRequirement.objects.filter(role=role, enabled=True, deleted_at__isnull=True)
        .order_by("scope_level")  # "org" prima di "plant": deterministico
        .first()
    )
    if req is not None:
        return req.single_holder
    return role not in DEFAULT_MULTI_HOLDER_ROLES


def get_vacant_mandatory_roles(plant=None):
    """Ruoli obbligatori (``RoleRequirement``) senza titolare attivo.

    Senza ``plant`` la vista è org-wide: un ruolo è vacante se non ha alcuna
    nomina attiva nel suo scope (org per i ruoli org-level; nessuna nomina di
    sito — né fallback org dove previsto — per i ruoli per-sito). Con ``plant``
    valuta la copertura del singolo sito (rispettando ``applies_to`` e il
    fallback org ``org_covers_sites``).

    Ritorna una lista di codici ruolo (compatibile con il cockpit advisor e
    l'endpoint ``/vacanti``).
    """
    from .models import RoleRequirement

    vacant = []
    requirements = RoleRequirement.objects.filter(
        enabled=True, mandatory=True, deleted_at__isnull=True,
    )

    for req in requirements:
        if req.scope_level == "org":
            covered = _active_role_qs(req.role).filter(scope_type="org").exists()
        else:  # per-sito
            if plant is not None and req.applies_to == "nis2_only" and not plant.is_nis2_subject:
                continue  # requisito non applicabile a questo sito
            if plant is not None:
                site = _active_role_qs(req.role).filter(
                    scope_type="plant", scope_id=plant.pk,
                ).exists()
            else:
                site = _active_role_qs(req.role).filter(scope_type="plant").exists()
            org = req.org_covers_sites and _active_role_qs(req.role).filter(
                scope_type="org",
            ).exists()
            covered = site or org
        if not covered and req.role not in vacant:
            vacant.append(req.role)

    return vacant


def get_role_coverage_matrix(user, expiring_days: int = 30):
    """Matrice di copertura dei ruoli per scope.

    Restituisce tre blocchi:
    - ``org_roles``: ruoli org-level **obbligatori** con stato unico;
    - ``plant_roles``: matrice completa — TUTTI i ruoli normativi tranne quelli
      definiti come org-level obbligatori — con una cella per ogni plant
      visibile. I ruoli obbligatori per-sito segnalano le lacune (``vacant``);
      gli altri sono assegnabili ma neutri (``unset``);
    - ``plants``: anagrafica dei plant visibili (raggruppabili per BU lato UI).

    Stati cella: ``covered`` (titolare di sito), ``covered_via_org`` (ereditato
    dal titolare org quando ``org_covers_sites=True``), ``expiring``, ``vacant``
    (obbligatorio e scoperto), ``unset`` (non obbligatorio e senza titolare),
    ``na`` (requisito non applicabile al sito).
    """
    from .models import NormativeRole, RoleAssignment, RoleRequirement
    from apps.plants.models import Plant
    from core.scoping import get_user_plant_ids

    today = timezone.localdate()
    threshold = today + timezone.timedelta(days=expiring_days)

    requirements = list(
        RoleRequirement.objects.filter(enabled=True, deleted_at__isnull=True)
    )
    org_mandatory = {r.role for r in requirements if r.scope_level == "org" and r.mandatory}
    # Requisito per-sito (obbligatorio) per ruolo: definisce applies_to/fallback
    site_req = {
        r.role: r for r in requirements
        if r.scope_level == "plant" and r.mandatory
    }
    single_by_role = {r.role: r.single_holder for r in requirements}

    all_roles = [code for code, _ in NormativeRole.choices]
    site_row_roles = [r for r in all_roles if r not in org_mandatory]

    # Plant visibili all'utente (scoping plant — niente PII di siti non accessibili)
    allowed = get_user_plant_ids(user)
    plants_qs = Plant.objects.select_related("bu").filter(deleted_at__isnull=True)
    if allowed is not None:
        plants_qs = plants_qs.filter(id__in=allowed)
    plants = list(plants_qs.order_by("bu__code", "code"))

    # Tutte le assegnazioni attive: una sola query (no N+1)
    active = (
        RoleAssignment.objects.filter(
            role__in=all_roles,
            valid_from__lte=today,
            deleted_at__isnull=True,
        )
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today))
        .select_related("user")
    )

    org_by_role: dict = {}          # role -> [assignment]
    plant_by_role_site: dict = {}   # (role, str(scope_id)) -> [assignment]
    for a in active:
        if a.scope_type == "org":
            org_by_role.setdefault(a.role, []).append(a)
        elif a.scope_type == "plant" and a.scope_id:
            plant_by_role_site.setdefault((a.role, str(a.scope_id)), []).append(a)

    def holder(a):
        return {
            "id": str(a.id),
            "user": (a.user.get_full_name() or a.user.email) if a.user_id else None,
            "valid_until": str(a.valid_until) if a.valid_until else None,
            "days_left": (a.valid_until - today).days if a.valid_until else None,
        }

    def evaluate(assignments, empty_status):
        """(status, holders): empty_status distingue obbligatorio (vacant) da non (unset)."""
        if not assignments:
            return empty_status, []
        holders = [holder(a) for a in assignments]
        all_expiring = all(
            a.valid_until is not None and a.valid_until <= threshold
            for a in assignments
        )
        return ("expiring" if all_expiring else "covered"), holders

    # ── Ruoli org-level obbligatori ──
    org_roles = []
    for r in sorted((x for x in requirements if x.scope_level == "org" and x.mandatory),
                    key=lambda x: x.role):
        status, holders = evaluate(org_by_role.get(r.role, []), "vacant")
        org_roles.append({
            "role": r.role,
            "framework_refs": r.framework_refs,
            "status": status,
            "holders": holders,
        })

    # ── Matrice completa per-sito ──
    plant_roles = []
    for role in sorted(site_row_roles):
        req = site_req.get(role)
        required = req is not None
        applies_to = req.applies_to if req else "all"
        org_covers = req.org_covers_sites if req else False
        empty_status = "vacant" if required else "unset"

        cells = {}
        for p in plants:
            if required and applies_to == "nis2_only" and not p.is_nis2_subject:
                cells[str(p.id)] = {"status": "na", "holders": []}
                continue
            site_assigns = plant_by_role_site.get((role, str(p.id)), [])
            if site_assigns:
                status, holders = evaluate(site_assigns, empty_status)
                cells[str(p.id)] = {"status": status, "holders": holders}
            elif org_covers and org_by_role.get(role):
                status, holders = evaluate(org_by_role[role], empty_status)
                cells[str(p.id)] = {
                    "status": "expiring" if status == "expiring" else "covered_via_org",
                    "holders": holders,
                    "via_org": True,
                }
            else:
                cells[str(p.id)] = {"status": empty_status, "holders": []}

        plant_roles.append({
            "role": role,
            "required": required,
            "single_holder": single_by_role.get(role, role not in DEFAULT_MULTI_HOLDER_ROLES),
            "framework_refs": req.framework_refs if req else [],
            "applies_to": applies_to,
            "org_covers_sites": org_covers,
            "cells": cells,
        })

    plants_out = [
        {
            "id": str(p.id),
            "code": p.code,
            "name": p.name,
            "bu_id": str(p.bu_id) if p.bu_id else None,
            "bu_code": p.bu.code if p.bu_id else None,
            "bu_name": p.bu.name if p.bu_id else None,
            "nis2_scope": p.nis2_scope,
            "is_nis2": p.is_nis2_subject,
        }
        for p in plants
    ]

    return {"org_roles": org_roles, "plant_roles": plant_roles, "plants": plants_out}


def check_nis2_contact_active(plant) -> bool:
    from .models import NormativeRole, RoleAssignment

    today = timezone.localdate()
    return RoleAssignment.objects.filter(
        role=NormativeRole.NIS2_CONTACT,
        scope_type="plant",
        scope_id=plant.pk,
        valid_from__lte=today,
        deleted_at__isnull=True,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today)).exists()


def _match_policy_for_plant(policies_qs, plant):
    """
    Restituisce la policy più specifica applicabile al plant:
    - prima tenta match plant
    - poi BU
    - infine org
    """
    if plant:
        p_plant = policies_qs.filter(scope_type="plant", scope_id=plant.pk).first()
        if p_plant:
            return p_plant
        if getattr(plant, "bu_id", None):
            p_bu = policies_qs.filter(scope_type="bu", scope_id=plant.bu_id).first()
            if p_bu:
                return p_bu
    return policies_qs.filter(scope_type="org").first()


def resolve_document_workflow_policy(document_type: str, plant=None):
    """
    Trova la policy di workflow documentale applicabile per tipo documento e plant.
    """
    from .models import DocumentWorkflowPolicy

    qs = DocumentWorkflowPolicy.objects.filter(
        document_type=document_type,
        deleted_at__isnull=True,
    )
    return _match_policy_for_plant(qs, plant)


def user_has_document_permission(user, document, action: str) -> bool:
    """
    Verifica se l'utente ha il permesso governance per l'azione richiesta
    sul documento M07 in base a DocumentWorkflowPolicy + RoleAssignment.

    action: "submit" | "review" | "approve"
    """
    from .models import RoleAssignment

    if not user.is_authenticated:
        return False

    # Superuser Django sempre ammesso
    if getattr(user, "is_superuser", False):
        return True

    doc_type = getattr(document, "document_type", None) or "altro"
    plant = getattr(document, "plant", None)
    policy = resolve_document_workflow_policy(doc_type, plant)
    if not policy:
        # Se non esiste policy esplicita, fallback: nessun blocco aggiuntivo
        return True

    role_field = {
        "submit": "submit_roles",
        "review": "review_roles",
        "approve": "approve_roles",
    }.get(action)
    if not role_field:
        return False

    target_roles = getattr(policy, role_field, []) or []
    if not target_roles:
        # Policy definita ma lista ruoli vuota → nessun vincolo aggiuntivo
        return True

    today = timezone.localdate()
    qs = RoleAssignment.objects.filter(
        user=user,
        role__in=target_roles,
        valid_from__lte=today,
        deleted_at__isnull=True,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today))

    if plant:
        qs = qs.filter(
            Q(scope_type="org") |
            Q(scope_type="plant", scope_id=plant.pk)
        )

    return qs.exists()


def resolve_document_recipients(document, action: str) -> list[str]:
    """
    Restituisce le email dei destinatari governance per un documento M07
    in base a DocumentWorkflowPolicy + RoleAssignment.

    action: "submit" | "review" | "approve"
    """
    from django.contrib.auth import get_user_model
    from .models import RoleAssignment

    User = get_user_model()
    doc_type = getattr(document, "document_type", None) or "altro"
    plant = getattr(document, "plant", None)
    policy = resolve_document_workflow_policy(doc_type, plant)
    if not policy:
        return []

    field_map = {
        "submit": "submit_roles",
        "review": "review_roles",
        "approve": "approve_roles",
    }
    role_field = field_map.get(action)
    if not role_field:
        return []

    target_roles = getattr(policy, role_field, []) or []
    if not target_roles:
        return []

    today = timezone.localdate()
    qs = RoleAssignment.objects.filter(
        role__in=target_roles,
        valid_from__lte=today,
        deleted_at__isnull=True,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today))

    if plant:
        qs = qs.filter(
            Q(scope_type="org") |
            Q(scope_type="plant", scope_id=plant.pk)
        )

    user_ids = qs.values_list("user_id", flat=True).distinct()
    users = User.objects.filter(
        pk__in=user_ids,
        is_active=True,
    ).exclude(email__isnull=True).exclude(email__exact="")
    return list(users.values_list("email", flat=True))


# ── Assegnazioni di ruolo duplicate ─────────────────────────────────────────

def system_actor():
    """Utente a cui attribuire l'audit delle azioni automatiche (migrazioni,
    manutenzioni senza operatore): il primo superuser attivo, o None."""
    from django.contrib.auth import get_user_model

    return (
        get_user_model().objects.filter(is_superuser=True, is_active=True)
        .order_by("date_joined").first()
    )


def create_role_assignment(data: dict, user):
    """Crea una nomina dopo aver escluso i doppioni.

    Controllo e creazione sono serializzati per (ruolo, perimetro) con un
    advisory lock di transazione: due salvataggi simultanei (doppio clic,
    doppio invio) non possono superare entrambi il controllo. Il vincolo DB
    `uniq_open_role_assignment` resta l'ultima difesa per lo stesso utente.
    Solleva ValidationError con messaggio sul campo `role`.
    """
    from django.core.exceptions import ValidationError
    from django.db import IntegrityError, connection, transaction
    from django.utils.translation import gettext_lazy as _
    from core.audit import log_action
    from .models import RoleAssignment

    role = data.get("role")
    scope_type = data.get("scope_type")
    scope_id = data.get("scope_id")
    same_user_msg = _("Questo utente ha già questo ruolo attivo per questo perimetro.")
    today = timezone.localdate()

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s))",
                [f"governance.role_assignment:{role}:{scope_type}:{scope_id or ''}"],
            )
        active = RoleAssignment.objects.filter(
            role=role, scope_type=scope_type, scope_id=scope_id,
        ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today))
        if is_single_holder(role) and active.exists():
            raise ValidationError({"role": _(
                "Questo ruolo ha già un titolare attivo per questo "
                "perimetro. Usa Sostituisci per cambiare il titolare."
            )})
        if active.filter(user=data.get("user")).exists():
            raise ValidationError({"role": same_user_msg})
        try:
            with transaction.atomic():
                instance = RoleAssignment.objects.create(created_by=user, **data)
        except IntegrityError:
            raise ValidationError({"role": same_user_msg}) from None

        log_action(
            user=user,
            action_code="governance.role_assignment.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id)},
        )
    return instance


def find_duplicate_role_assignments() -> list[dict]:
    """Nomine "aperte" (non eliminate, senza data di fine) dello stesso utente
    sullo stesso ruolo e perimetro: le righe che `uniq_open_role_assignment`
    non ammette. Per ogni gruppo si tiene la nomina più vecchia (`keep`, la
    data di inizio reale) e si elencano le altre (`remove`)."""
    from .models import RoleAssignment

    groups: dict[tuple, list] = {}
    rows = RoleAssignment.objects.filter(valid_until__isnull=True).order_by("valid_from", "created_at")
    for ra in rows:
        groups.setdefault((ra.user_id, ra.role, ra.scope_type, ra.scope_id), []).append(ra)
    return [
        {
            "user_id": key[0], "role": key[1], "scope_type": key[2], "scope_id": key[3],
            "keep": items[0], "remove": items[1:],
        }
        for key, items in groups.items()
        if len(items) > 1
    ]


def cleanup_duplicate_role_assignments(actor) -> int:
    """Soft delete dei doppioni trovati da `find_duplicate_role_assignments`,
    con audit trail per ciascuna nomina rimossa. Idempotente. Ritorna il numero
    di nomine rimosse."""
    from django.db import transaction
    from core.audit import log_action

    removed = 0
    with transaction.atomic():
        for group in find_duplicate_role_assignments():
            keep = group["keep"]
            for dup in group["remove"]:
                dup.soft_delete()
                log_action(
                    user=actor,
                    action_code="governance.role_assignment.duplicate_removed",
                    level="L2",
                    entity=dup,
                    payload={
                        "role": dup.role,
                        "scope_type": dup.scope_type,
                        "scope_id": str(dup.scope_id) if dup.scope_id else None,
                        "kept_assignment": str(keep.pk),
                    },
                )
                removed += 1
    return removed


def find_single_holder_conflicts() -> list[dict]:
    """Ruoli a titolare unico con più titolari attivi *diversi* sullo stesso
    perimetro. Non si risolvono in automatico: chi resta lo decide il
    responsabile, da Governance con Sostituisci o Termina."""
    from .models import RoleAssignment

    today = timezone.localdate()
    holders: dict[tuple, set] = {}
    active = RoleAssignment.objects.filter(valid_from__lte=today).filter(
        Q(valid_until__isnull=True) | Q(valid_until__gte=today)
    )
    for ra in active:
        holders.setdefault((ra.role, ra.scope_type, ra.scope_id), set()).add(ra.user_id)

    single_cache: dict[str, bool] = {}
    conflicts = []
    for (role, scope_type, scope_id), user_ids in holders.items():
        if len(user_ids) < 2:
            continue
        if role not in single_cache:
            single_cache[role] = is_single_holder(role)
        if single_cache[role]:
            conflicts.append({
                "role": role, "scope_type": scope_type, "scope_id": scope_id,
                "user_ids": sorted(user_ids),
            })
    return conflicts


# ══════════════════════════════════════════════════════════════════════════
# Obiettivi di sicurezza (ISO/IEC 27001:2022 §6.2)
# ══════════════════════════════════════════════════════════════════════════
#
# Le soglie del KPI e il target dell'obiettivo rispondono a due domande
# diverse e non vanno confuse: la soglia dice "siamo sotto il livello
# accettabile adesso?", l'obiettivo dice "arriveremo al target entro la
# scadenza?". Qui si calcola solo la seconda. La prima resta in
# apps.tasks.services.evaluate_kpi_status e non viene toccata.

# Stati della traiettoria — non sono lo stato del record (`status`), che è la
# decisione umana, ma la lettura automatica dell'andamento.
TRACK_ON_TRACK = "in_linea"
TRACK_AT_RISK = "a_rischio"
TRACK_MISSED = "mancato"
TRACK_NO_DATA = "senza_misure"
TRACK_NOT_APPLICABLE = "non_applicabile"

# Quanti punti percentuali di ritardo sul cammino previsto si tollerano prima
# di dichiarare la traiettoria a rischio. Con meno margine un obiettivo che
# progredisce a scatti (tipico: una campagna che chiude a blocchi) verrebbe
# segnalato a ogni pausa.
AT_RISK_GAP_PCT = 15.0

OBJECTIVE_OPEN_STATUSES = ("bozza", "attivo", "sospeso")

# Sentinella: `value=None` significa "misurato e non disponibile", mentre
# l'assenza dell'argomento significa "caricalo tu". Senza distinguerli,
# ogni obiettivo senza misure rifarebbe la query in objectives_overview.
_UNSET = object()


def _objective_audit(user, objective, action, payload=None):
    from core.audit import log_action

    log_action(
        user=user,
        action_code=f"governance.security_objective.{action}",
        level="L2",
        entity=objective,
        payload={"id": str(objective.id), "code": objective.code, **(payload or {})},
    )


def objective_unit(objective) -> str:
    """Unità di misura effettiva: quella del KPI se l'obiettivo è agganciato."""
    if objective.measure_source == "kpi" and objective.kpi_definition_id:
        return objective.kpi_definition.unit or ""
    return objective.unit or ""


def objective_progress_pct(objective, value):
    """Percentuale del cammino baseline → target già percorsa.

    La formula è indifferente alla direzione: per un obiettivo "below"
    (es. ridurre i giorni dall'ultimo test di ripristino) sia numeratore sia
    denominatore sono negativi quando si migliora, e il rapporto resta
    positivo. Restituisce None se manca la baseline o se baseline e target
    coincidono (non c'è cammino da percorrere: l'obiettivo non dice nulla).
    """
    if value is None or objective.baseline_value is None:
        return None
    span = objective.target_value - objective.baseline_value
    if span == 0:
        return None
    pct = (value - objective.baseline_value) / span * 100.0
    # Sotto la baseline si è tornati indietro: si riporta il valore negativo
    # invece di azzerarlo, perché "peggio di quando abbiamo iniziato" è
    # un'informazione che la direzione deve vedere.
    return round(pct, 1)


def objective_elapsed_pct(objective, today) -> float | None:
    """Percentuale di tempo consumato fra start_date e target_date."""
    span = (objective.target_date - objective.start_date).days
    if span <= 0:
        return None
    elapsed = (today - objective.start_date).days
    return round(max(0.0, min(elapsed / span * 100.0, 100.0)), 1)


def objective_is_reached(objective, value) -> bool:
    if value is None:
        return False
    if objective.target_direction == "below":
        return value <= objective.target_value
    return value >= objective.target_value


def _weak_target(objective) -> bool:
    """True se il target non è migliore della soglia di warning del KPI.

    Un obiettivo il cui traguardo coincide con la soglia di allerta non
    aggiunge nulla a ciò che il KPI già segnala ogni settimana: è la
    duplicazione da evitare. Non è un errore bloccante — la taratura resta una
    scelta di chi governa — ma va mostrata a chi lo configura.
    """
    if objective.measure_source != "kpi" or not objective.kpi_definition_id:
        return False
    warn = objective.kpi_definition.threshold_warning
    if warn is None:
        return False
    if objective.target_direction == "below":
        return objective.target_value >= warn
    return objective.target_value <= warn


def latest_objective_values(objectives) -> dict:
    """{objective_id: (value, date)} per un insieme di obiettivi, senza N+1.

    Due query in tutto: una sulle misure manuali, una sugli snapshot KPI.
    """
    from apps.tasks.models import OperationalKpiSnapshot
    from .models import SecurityObjectiveMeasurement

    objectives = list(objectives)
    out: dict = {}

    manual_ids = [o.id for o in objectives if o.measure_source == "manual"]
    if manual_ids:
        # ordering del modello = -measured_on: il primo per obiettivo è l'ultimo
        # misurato, quindi setdefault tiene quello giusto.
        for m in SecurityObjectiveMeasurement.objects.filter(
            objective_id__in=manual_ids
        ).order_by("objective_id", "-measured_on"):
            out.setdefault(m.objective_id, (m.value, m.measured_on))

    kpi_objs = [o for o in objectives if o.measure_source == "kpi" and o.kpi_definition_id]
    if kpi_objs:
        kpi_ids = {o.kpi_definition_id for o in kpi_objs}
        snaps = (
            OperationalKpiSnapshot.objects.filter(
                kpi_definition_id__in=kpi_ids, value__isnull=False
            )
            .order_by("kpi_definition_id", "-week_start", "-created_at")
            .values_list("kpi_definition_id", "plant_id", "value", "week_start")
        )
        by_kpi: dict = {}
        for kpi_id, plant_id, value, week_start in snaps:
            by_kpi.setdefault((kpi_id, plant_id), (value, week_start))
        for o in kpi_objs:
            # Obiettivo di sito → snapshot del sito, con ripiego sullo snapshot
            # globale (KPI alimentati via API, che non hanno riga per sito).
            hit = by_kpi.get((o.kpi_definition_id, o.plant_id)) or by_kpi.get(
                (o.kpi_definition_id, None)
            )
            if hit:
                out[o.id] = hit
    return out


def objective_series(objective, limit: int = 52) -> list[dict]:
    """Serie storica delle misure, dalla più vecchia alla più recente.

    Unico accesso per entrambe le sorgenti, così chi consuma il dato (grafico,
    relazione del riesame) non deve sapere da dove arriva il numero.
    """
    from apps.tasks.models import OperationalKpiSnapshot
    from .models import SecurityObjectiveMeasurement

    if objective.measure_source == "manual":
        rows = (
            SecurityObjectiveMeasurement.objects.filter(objective=objective)
            .filter(measured_on__gte=objective.start_date)
            .order_by("-measured_on")
            .values_list("measured_on", "value")[:limit]
        )
    elif objective.kpi_definition_id:
        qs = OperationalKpiSnapshot.objects.filter(
            kpi_definition_id=objective.kpi_definition_id,
            value__isnull=False,
            week_start__gte=objective.start_date,
        )
        qs = qs.filter(plant_id=objective.plant_id) if objective.plant_id else qs
        rows = qs.order_by("-week_start").values_list("week_start", "value")[:limit]
    else:
        rows = []
    return [{"date": d.isoformat(), "value": v} for d, v in reversed(list(rows))]


def evaluate_objective(objective, *, value=_UNSET, measured_on=None, today=None) -> dict:
    """Lettura dell'andamento: valore corrente, progresso, traiettoria.

    `value`/`measured_on` si passano quando sono già stati caricati in blocco
    (vedi `latest_objective_values`), per non rifare una query per riga.
    """
    from apps.plants.services import plant_today

    # La mezzanotte che conta per una scadenza è quella del sito (F3).
    today = today or plant_today(objective.plant)
    if value is _UNSET:
        value, measured_on = latest_objective_values([objective]).get(
            objective.id, (None, None)
        )

    progress = objective_progress_pct(objective, value)
    elapsed = objective_elapsed_pct(objective, today)
    reached = objective_is_reached(objective, value)

    if objective.status in ("raggiunto", "non_raggiunto", "annullato"):
        track = TRACK_NOT_APPLICABLE
    elif value is None:
        track = TRACK_NO_DATA
    elif reached:
        track = TRACK_ON_TRACK
    elif today > objective.target_date:
        track = TRACK_MISSED
    elif progress is None or elapsed is None:
        # Senza baseline o senza durata non si può parlare di traiettoria: si
        # dice solo che l'obiettivo non è ancora raggiunto, senza inventare un
        # giudizio.
        track = TRACK_NO_DATA
    elif progress + AT_RISK_GAP_PCT < elapsed:
        track = TRACK_AT_RISK
    else:
        track = TRACK_ON_TRACK

    return {
        "current_value": value,
        "measured_on": measured_on.isoformat() if measured_on else None,
        "unit": objective_unit(objective),
        "progress_pct": progress,
        "elapsed_pct": elapsed,
        "reached": reached,
        "track": track,
        "days_to_target": (objective.target_date - today).days,
        "weak_target": _weak_target(objective),
    }


def _validate_objective(data, instance=None):
    """Coerenza fra sorgente della misura, sito e traiettoria."""
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    def field(name, default=None):
        if name in data:
            return data[name]
        return getattr(instance, name, default) if instance else default

    measure_source = field("measure_source", "kpi")
    kpi = field("kpi_definition")
    if measure_source == "kpi" and kpi is None:
        raise ValidationError({"kpi_definition": _("Indicare il KPI da cui leggere le misure.")})
    if measure_source == "manual" and kpi is not None:
        raise ValidationError({
            "kpi_definition": _("Un obiettivo a misura manuale non può essere agganciato a un KPI.")
        })

    plant = field("plant")
    if kpi is not None and kpi.plant_id and plant is not None and kpi.plant_id != plant.id:
        raise ValidationError({"kpi_definition": _("Il KPI appartiene a un altro sito.")})
    if kpi is not None and kpi.plant_id and plant is None:
        raise ValidationError({
            "kpi_definition": _("Un obiettivo di organizzazione non può usare un KPI di un singolo sito.")
        })

    start_date, target_date = field("start_date"), field("target_date")
    if start_date and target_date and target_date <= start_date:
        raise ValidationError({"target_date": _("La scadenza deve essere successiva all'inizio del periodo.")})

    baseline, target = field("baseline_value"), field("target_value")
    if baseline is not None and target is not None and baseline == target:
        raise ValidationError({
            "target_value": _("Il target coincide con il valore di partenza: non c'è alcun miglioramento da misurare.")
        })
    direction = field("target_direction", "above")
    if baseline is not None and target is not None:
        improving = target > baseline if direction == "above" else target < baseline
        if not improving:
            raise ValidationError({
                "target_value": _("Il target peggiora il valore di partenza nella direzione indicata.")
            })


def create_objective(serializer, user):
    _validate_objective(serializer.validated_data)
    objective = serializer.save(created_by=user)
    _objective_audit(user, objective, "create", {
        "plant_id": str(objective.plant_id) if objective.plant_id else None,
        "measure_source": objective.measure_source,
        "target_value": objective.target_value,
        "target_date": objective.target_date.isoformat(),
    })
    return objective


def update_objective(serializer, user):
    """Aggiorna un obiettivo.

    §6.2 vuole obiettivi aggiornabili, ma un target che si sposta senza
    lasciare traccia svuota l'impegno: i cambi di traiettoria su un obiettivo
    attivo finiscono nell'audit con valore precedente e nuovo. Un obiettivo
    chiuso non si riapre da qui.
    """
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    instance = serializer.instance
    if instance.status in ("raggiunto", "non_raggiunto", "annullato"):
        raise ValidationError(_("L'obiettivo è chiuso: non è più modificabile."))

    _validate_objective(serializer.validated_data, instance=instance)
    tracked = ("target_value", "target_date", "baseline_value", "target_direction", "owner_role")
    before = {f: getattr(instance, f) for f in tracked}
    objective = serializer.save()

    changed = {
        f: {"da": before[f].isoformat() if hasattr(before[f], "isoformat") else before[f],
            "a": getattr(objective, f).isoformat()
            if hasattr(getattr(objective, f), "isoformat") else getattr(objective, f)}
        for f in tracked
        if before[f] != getattr(objective, f)
    }
    _objective_audit(user, objective, "update", {"changed": changed} if changed else None)
    return objective


def activate_objective(objective, user):
    """Da bozza ad attivo: l'impegno diventa formale, quindi il piano §6.2
    (chi risponde, come si valuta) deve essere completo."""
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    if objective.status not in ("bozza", "sospeso"):
        raise ValidationError(_("Solo un obiettivo in bozza o sospeso può essere attivato."))
    missing = []
    if not objective.owner_role:
        missing.append(_("il ruolo responsabile"))
    if not objective.evaluation_method:
        missing.append(_("il metodo di valutazione del risultato"))
    if missing:
        raise ValidationError(
            _("Per attivare l'obiettivo indicare: %(fields)s.") % {"fields": ", ".join(missing)}
        )
    previous, objective.status = objective.status, "attivo"
    objective.save(update_fields=["status", "updated_at"])
    _objective_audit(user, objective, "activate", {"da": previous})
    return objective


def suspend_objective(objective, user, note=""):
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    if objective.status != "attivo":
        raise ValidationError(_("Solo un obiettivo attivo può essere sospeso."))
    objective.status = "sospeso"
    objective.save(update_fields=["status", "updated_at"])
    _objective_audit(user, objective, "suspend", {"note": bool(note)})
    return objective


def close_objective(objective, user, outcome, note=""):
    """Chiude l'obiettivo dichiarando l'esito.

    L'esito lo dichiara una persona, non il calcolo: il sistema sa dire se il
    target è stato raggiunto, ma solo la direzione decide se l'impegno si
    considera chiuso. Un obiettivo mancato resta mancato a verbale — è il dato
    che serve al riesame, e da lì nasce eventualmente un PDCA.
    """
    from django.core.exceptions import ValidationError
    from django.utils import timezone as dj_timezone
    from django.utils.translation import gettext as _

    if outcome not in ("raggiunto", "non_raggiunto", "annullato"):
        raise ValidationError(_("Esito non valido."))
    if objective.status not in OBJECTIVE_OPEN_STATUSES:
        raise ValidationError(_("L'obiettivo è già chiuso."))
    if outcome == "annullato" and not note:
        raise ValidationError({"note": _("Indicare il motivo dell'annullamento.")})

    evaluation = evaluate_objective(objective)
    objective.status = outcome
    objective.closed_at = dj_timezone.now()
    objective.closed_by = user
    objective.closure_note = note
    objective.save(update_fields=["status", "closed_at", "closed_by", "closure_note", "updated_at"])
    _objective_audit(user, objective, "close", {
        "outcome": outcome,
        "value_at_close": evaluation["current_value"],
        "target_value": objective.target_value,
    })
    return objective


def record_objective_measurement(objective, user, *, value, measured_on=None, note=""):
    """Registra una misura manuale.

    Vietata sugli obiettivi agganciati a un KPI: là la misura è lo snapshot
    settimanale del motore M08, e una misura scritta a mano creerebbe una
    seconda verità sullo stesso numero. Se un KPI non ha integrazione, il
    valore si inserisce sul KPI (`record_manual_kpi_value`), non qui.
    """
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _
    from apps.plants.services import plant_today
    from .models import SecurityObjectiveMeasurement

    if objective.measure_source != "manual":
        raise ValidationError(
            _("L'obiettivo è agganciato a un KPI: il valore si registra sul KPI.")
        )
    if objective.status not in ("attivo", "bozza"):
        raise ValidationError(_("Si possono registrare misure solo su un obiettivo aperto."))
    if value is None:
        raise ValidationError({"value": _("Indicare il valore misurato.")})

    measured_on = measured_on or plant_today(objective.plant)
    if isinstance(measured_on, str):
        # Dal payload API la data arriva come stringa: senza conversione il
        # confronto con start_date esploderebbe a runtime.
        from datetime import date as _date

        try:
            measured_on = _date.fromisoformat(measured_on)
        except ValueError:
            raise ValidationError({"measured_on": _("Data non valida (formato atteso: AAAA-MM-GG).")}) from None
    if measured_on < objective.start_date:
        raise ValidationError({
            "measured_on": _("La data della misura precede l'inizio del periodo.")
        })

    measurement, created = SecurityObjectiveMeasurement.objects.update_or_create(
        objective=objective,
        measured_on=measured_on,
        defaults={"value": value, "note": note, "created_by": user},
    )
    _objective_audit(user, objective, "measure", {
        "measured_on": measured_on.isoformat(), "value": value, "nuova": created,
    })
    return measurement


def objectives_overview(queryset, today=None) -> dict:
    """Conteggi per stato e per traiettoria su un insieme di obiettivi.

    Pensata per il cruscotto e, in fase 2, per lo snapshot del riesame di
    direzione (§9.3.2 d4). Il queryset arriva già ristretto al perimetro di
    chi chiede.
    """
    objectives = list(
        queryset.select_related("plant", "kpi_definition")
        if hasattr(queryset, "select_related") else queryset
    )
    values = latest_objective_values(objectives)
    by_status: dict = {}
    by_track: dict = {}
    for o in objectives:
        value, measured_on = values.get(o.id, (None, None))
        ev = evaluate_objective(o, value=value, measured_on=measured_on, today=today)
        by_status[o.status] = by_status.get(o.status, 0) + 1
        by_track[ev["track"]] = by_track.get(ev["track"], 0) + 1
    return {"totale": len(objectives), "per_stato": by_status, "per_traiettoria": by_track}

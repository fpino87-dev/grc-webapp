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
    requirements = RoleRequirement.objects.filter(enabled=True, deleted_at__isnull=True)

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
    """Matrice di copertura dei ruoli obbligatori per scope.

    Restituisce tre blocchi:
    - ``org_roles``: ruoli org-level con stato unico (covered/expiring/vacant);
    - ``plant_roles``: ruoli per-sito con una cella per ogni plant visibile;
    - ``plants``: anagrafica dei plant visibili (raggruppabili per BU lato UI).

    Stati cella: ``covered`` (titolare di sito), ``covered_via_org`` (ereditato
    dal titolare org quando ``org_covers_sites=True``), ``expiring``, ``vacant``,
    ``na`` (requisito non applicabile al sito).
    """
    from .models import RoleAssignment, RoleRequirement
    from apps.plants.models import Plant
    from core.scoping import get_user_plant_ids

    today = timezone.localdate()
    threshold = today + timezone.timedelta(days=expiring_days)

    requirements = list(
        RoleRequirement.objects.filter(enabled=True, deleted_at__isnull=True)
    )
    req_roles = {r.role for r in requirements}

    # Plant visibili all'utente (scoping plant — niente PII di siti non accessibili)
    allowed = get_user_plant_ids(user)
    plants_qs = Plant.objects.select_related("bu").filter(deleted_at__isnull=True)
    if allowed is not None:
        plants_qs = plants_qs.filter(id__in=allowed)
    plants = list(plants_qs.order_by("bu__code", "code"))

    # Tutte le assegnazioni attive dei ruoli richiesti: una sola query (no N+1)
    active = (
        RoleAssignment.objects.filter(
            role__in=req_roles,
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

    def evaluate(assignments):
        """(status, holders) per un insieme di assegnazioni dirette."""
        if not assignments:
            return "vacant", []
        holders = [holder(a) for a in assignments]
        all_expiring = all(
            a.valid_until is not None and a.valid_until <= threshold
            for a in assignments
        )
        return ("expiring" if all_expiring else "covered"), holders

    org_roles, plant_roles = [], []
    for r in sorted(requirements, key=lambda x: (x.scope_level, x.role)):
        if r.scope_level == "org":
            status, holders = evaluate(org_by_role.get(r.role, []))
            org_roles.append({
                "role": r.role,
                "framework_refs": r.framework_refs,
                "status": status,
                "holders": holders,
            })
            continue

        cells = {}
        for p in plants:
            if r.applies_to == "nis2_only" and not p.is_nis2_subject:
                cells[str(p.id)] = {"status": "na", "holders": []}
                continue
            site_assigns = plant_by_role_site.get((r.role, str(p.id)), [])
            if site_assigns:
                status, holders = evaluate(site_assigns)
                cells[str(p.id)] = {"status": status, "holders": holders}
            elif r.org_covers_sites and org_by_role.get(r.role):
                status, holders = evaluate(org_by_role[r.role])
                cells[str(p.id)] = {
                    "status": "expiring" if status == "expiring" else "covered_via_org",
                    "holders": holders,
                    "via_org": True,
                }
            else:
                cells[str(p.id)] = {"status": "vacant", "holders": []}
        plant_roles.append({
            "role": r.role,
            "framework_refs": r.framework_refs,
            "applies_to": r.applies_to,
            "org_covers_sites": r.org_covers_sites,
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


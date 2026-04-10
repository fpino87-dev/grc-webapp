from django.db.models import Q
from django.utils import timezone


def get_active_role(user, role: str, scope_id=None):
    from .models import RoleAssignment

    today = timezone.now().date()
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

    today = timezone.now().date()
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

    termination_date = termination_date or timezone.now().date()
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
            "reason":           reason,
        },
    )
    return assignment


def replace_role(old_assignment, new_user, user,
                 handover_date=None, reason="", document_id=None):
    """Successione atomica: termina il vecchio ruolo e crea il nuovo."""
    from django.db import transaction
    from core.audit import log_action
    from .models import RoleAssignment

    handover_date = handover_date or timezone.now().date()

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
                "reason":        reason,
            },
        )

    return old_assignment, new_assignment


def get_expiring_roles(days=30):
    """Ruoli in scadenza nei prossimi N giorni o già scaduti."""
    from .models import RoleAssignment

    today     = timezone.now().date()
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


def get_vacant_mandatory_roles(plant=None):
    """Ruoli NIS2/ISO obbligatori senza titolare attivo."""
    from .models import RoleAssignment

    MANDATORY_ROLES = ["nis2_contact", "ciso", "isms_manager", "dpo"]
    today = timezone.now().date()
    vacant = []

    for role in MANDATORY_ROLES:
        qs = RoleAssignment.objects.filter(
            role=role,
            valid_from__lte=today,
            deleted_at__isnull=True,
        ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today))
        if plant:
            qs = qs.filter(
                Q(scope_type="org") |
                Q(scope_type="plant", scope_id=plant.pk)
            )
        if not qs.exists():
            vacant.append(role)

    return vacant


def check_nis2_contact_active(plant) -> bool:
    from .models import NormativeRole, RoleAssignment

    today = timezone.now().date()
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
    from .models import NormativeRole, RoleAssignment

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

    today = timezone.now().date()
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

    today = timezone.now().date()
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


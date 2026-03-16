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


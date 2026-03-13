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


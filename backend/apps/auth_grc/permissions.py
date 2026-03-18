from rest_framework.permissions import BasePermission

from .models import GrcRole, UserPlantAccess


class IsGrcSuperAdmin(BasePermission):
    """
    Permette accesso solo ai super admin GRC.

    Regole:
    - utente autenticato
    - oppure Django superuser
    - oppure ha un UserPlantAccess con role=super_admin a livello org
    """

    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "is_superuser", False):
            return True
        return UserPlantAccess.objects.filter(
            user=user,
            role=GrcRole.SUPER_ADMIN,
            scope_type="org",
        ).exists()


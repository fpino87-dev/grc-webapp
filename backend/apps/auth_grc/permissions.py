from rest_framework.permissions import BasePermission

from core.permissions import RoleScopedPermission

from .models import GrcRole, UserPlantAccess


class CompetencyPermission(RoleScopedPermission):
    """Catalogo competenze (ISO 27001 7.2) e competenze utente: lettura per tutti
    i ruoli GRC (servono al gap analysis), scrittura ai soli super_admin /
    compliance_officer (definizione requisiti e verifica formale)."""
    read_roles = set(GrcRole.values)
    write_roles = {GrcRole.SUPER_ADMIN, GrcRole.COMPLIANCE_OFFICER}


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


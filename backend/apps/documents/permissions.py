"""RBAC modulo Documents (newfix F1)."""
from apps.auth_grc.models import GrcRole
from core.permissions import RoleScopedPermission


class DocumentPermission(RoleScopedPermission):
    """Tutti i ruoli operativi possono leggere (i record sono gia' scopati
    da DocumentViewSet.get_queryset per owner/shared/org); scrittura per chi
    gestisce documenti / evidenze."""
    read_roles = {
        GrcRole.SUPER_ADMIN,
        GrcRole.COMPLIANCE_OFFICER,
        GrcRole.RISK_MANAGER,
        GrcRole.PLANT_MANAGER,
        GrcRole.CONTROL_OWNER,
        GrcRole.INTERNAL_AUDITOR,
        GrcRole.EXTERNAL_AUDITOR,
    }
    write_roles = {
        GrcRole.SUPER_ADMIN,
        GrcRole.COMPLIANCE_OFFICER,
        GrcRole.RISK_MANAGER,
        GrcRole.PLANT_MANAGER,
        GrcRole.CONTROL_OWNER,
    }

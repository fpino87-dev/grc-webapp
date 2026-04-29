"""RBAC modulo BCP (newfix F1)."""
from apps.auth_grc.models import GrcRole
from core.permissions import RoleScopedPermission


_OWNERS = {
    GrcRole.SUPER_ADMIN,
    GrcRole.COMPLIANCE_OFFICER,
    GrcRole.RISK_MANAGER,
    GrcRole.PLANT_MANAGER,
}


class BcpPermission(RoleScopedPermission):
    """Owner BCP scrivono; auditor leggono per evidence raccolta."""
    read_roles = _OWNERS | {GrcRole.INTERNAL_AUDITOR, GrcRole.EXTERNAL_AUDITOR}
    write_roles = _OWNERS

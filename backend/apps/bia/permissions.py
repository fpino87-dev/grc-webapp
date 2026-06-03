"""RBAC modulo BIA (M05) — P1-3 SoD write-authorization."""
from apps.auth_grc.models import GrcRole
from core.permissions import RoleScopedPermission

_OPERATIONAL = {
    GrcRole.SUPER_ADMIN,
    GrcRole.COMPLIANCE_OFFICER,
    GrcRole.RISK_MANAGER,
    GrcRole.PLANT_MANAGER,
}
_AUDIT = {GrcRole.INTERNAL_AUDITOR, GrcRole.EXTERNAL_AUDITOR}


class BiaPermission(RoleScopedPermission):
    """Processi critici/decisioni di trattamento: lettura allargata, scrittura
    ai ruoli di governance (approvazione/validazione processi)."""
    read_roles = _OPERATIONAL | _AUDIT | {GrcRole.CONTROL_OWNER}
    write_roles = _OPERATIONAL

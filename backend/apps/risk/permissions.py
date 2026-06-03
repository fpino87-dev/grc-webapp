"""RBAC modulo Risk Assessment (M06) — P1-3 SoD write-authorization."""
from apps.auth_grc.models import GrcRole
from core.permissions import RoleScopedPermission

_OPERATIONAL = {
    GrcRole.SUPER_ADMIN,
    GrcRole.COMPLIANCE_OFFICER,
    GrcRole.RISK_MANAGER,
    GrcRole.PLANT_MANAGER,
}
_AUDIT = {GrcRole.INTERNAL_AUDITOR, GrcRole.EXTERNAL_AUDITOR}


class RiskPermission(RoleScopedPermission):
    """Valutazioni/dimensioni/piani di mitigazione: lettura allargata (anche
    control_owner e auditor), scrittura ai soli ruoli di governance del rischio."""
    read_roles = _OPERATIONAL | _AUDIT | {GrcRole.CONTROL_OWNER}
    write_roles = _OPERATIONAL


class RiskAppetitePermission(RoleScopedPermission):
    """Policy di risk appetite: decisione di governance → scrittura ristretta."""
    read_roles = _OPERATIONAL | _AUDIT | {GrcRole.CONTROL_OWNER}
    write_roles = {GrcRole.SUPER_ADMIN, GrcRole.COMPLIANCE_OFFICER, GrcRole.RISK_MANAGER}

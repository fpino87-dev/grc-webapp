"""RBAC modulo PDCA (M11) — P1-3 SoD write-authorization."""
from apps.auth_grc.models import GrcRole
from core.permissions import RoleScopedPermission

_AUDIT = {GrcRole.INTERNAL_AUDITOR, GrcRole.EXTERNAL_AUDITOR}


class PdcaPermission(RoleScopedPermission):
    """Cicli di miglioramento: lettura allargata (auditor inclusi), scrittura ai
    ruoli operativi che conducono il PDCA (incl. control_owner)."""
    read_roles = {
        GrcRole.SUPER_ADMIN,
        GrcRole.COMPLIANCE_OFFICER,
        GrcRole.RISK_MANAGER,
        GrcRole.PLANT_MANAGER,
        GrcRole.CONTROL_OWNER,
    } | _AUDIT
    write_roles = {
        GrcRole.SUPER_ADMIN,
        GrcRole.COMPLIANCE_OFFICER,
        GrcRole.RISK_MANAGER,
        GrcRole.PLANT_MANAGER,
        GrcRole.CONTROL_OWNER,
    }

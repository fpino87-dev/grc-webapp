"""RBAC modulo Asset IT/OT (M04) — P1-3 SoD write-authorization."""
from apps.auth_grc.models import GrcRole
from core.permissions import RoleScopedPermission

_AUDIT = {GrcRole.INTERNAL_AUDITOR, GrcRole.EXTERNAL_AUDITOR}


class AssetPermission(RoleScopedPermission):
    """Inventario asset/zone/dipendenze: lettura allargata (anche auditor),
    scrittura ai ruoli operativi che gestiscono gli asset (incl. control_owner)."""
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

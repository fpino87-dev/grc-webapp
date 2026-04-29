"""RBAC modulo Compliance Schedule (newfix F1)."""
from apps.auth_grc.models import GrcRole
from core.permissions import RoleScopedPermission


class CompliancePolicyPermission(RoleScopedPermission):
    """Lettura allargata (dashboard scadenzario), scrittura solo a chi
    governa il calendario di compliance."""
    read_roles = {
        GrcRole.SUPER_ADMIN,
        GrcRole.COMPLIANCE_OFFICER,
        GrcRole.RISK_MANAGER,
        GrcRole.PLANT_MANAGER,
        GrcRole.CONTROL_OWNER,
        GrcRole.INTERNAL_AUDITOR,
        GrcRole.EXTERNAL_AUDITOR,
    }
    write_roles = {GrcRole.SUPER_ADMIN, GrcRole.COMPLIANCE_OFFICER}

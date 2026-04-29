"""RBAC modulo Controls (newfix F1)."""
from apps.auth_grc.models import GrcRole
from core.permissions import RoleScopedPermission


_ALL_OPERATIONAL = {
    GrcRole.SUPER_ADMIN,
    GrcRole.COMPLIANCE_OFFICER,
    GrcRole.RISK_MANAGER,
    GrcRole.PLANT_MANAGER,
    GrcRole.CONTROL_OWNER,
    GrcRole.INTERNAL_AUDITOR,
    GrcRole.EXTERNAL_AUDITOR,
}


class FrameworkPermission(RoleScopedPermission):
    """Framework normativi: lettura per tutti i ruoli, scrittura solo a chi
    governa il catalogo (super_admin/compliance_officer)."""
    read_roles = _ALL_OPERATIONAL
    write_roles = {GrcRole.SUPER_ADMIN, GrcRole.COMPLIANCE_OFFICER}


class ControlInstancePermission(RoleScopedPermission):
    """Instances di controllo: lettura per tutti, scrittura per chi ha
    responsabilita' operative sui controlli."""
    read_roles = _ALL_OPERATIONAL
    write_roles = {
        GrcRole.SUPER_ADMIN,
        GrcRole.COMPLIANCE_OFFICER,
        GrcRole.PLANT_MANAGER,
        GrcRole.CONTROL_OWNER,
    }


class ControlsReportPermission(RoleScopedPermission):
    """Gap analysis / export compliance: read-only ad audit + governance."""
    read_roles = {
        GrcRole.SUPER_ADMIN,
        GrcRole.COMPLIANCE_OFFICER,
        GrcRole.RISK_MANAGER,
        GrcRole.PLANT_MANAGER,
        GrcRole.INTERNAL_AUDITOR,
        GrcRole.EXTERNAL_AUDITOR,
    }
    write_roles = read_roles

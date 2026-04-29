"""RBAC modulo Reporting (newfix F1)."""
from apps.auth_grc.models import GrcRole
from core.permissions import RoleScopedPermission


class ReportingPermission(RoleScopedPermission):
    """Tutte le viste reporting sono read-only di fatto. Limitato a chi ha
    responsabilita' GRC: dashboard di compliance/rischio non e' destinata a
    control_owner / utenti operativi puri."""
    read_roles = {
        GrcRole.SUPER_ADMIN,
        GrcRole.COMPLIANCE_OFFICER,
        GrcRole.RISK_MANAGER,
        GrcRole.PLANT_MANAGER,
        GrcRole.INTERNAL_AUDITOR,
        GrcRole.EXTERNAL_AUDITOR,
    }
    write_roles = read_roles

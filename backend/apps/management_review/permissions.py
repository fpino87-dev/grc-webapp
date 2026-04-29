"""RBAC modulo Management Review (newfix F1)."""
from apps.auth_grc.models import GrcRole
from core.permissions import RoleScopedPermission


class ManagementReviewPermission(RoleScopedPermission):
    """ISO 27001 clausola 9.3: la revisione direzione coinvolge top management
    e auditor. Scrittura ristretta a CISO/Compliance Officer."""
    read_roles = {
        GrcRole.SUPER_ADMIN,
        GrcRole.COMPLIANCE_OFFICER,
        GrcRole.RISK_MANAGER,
        GrcRole.INTERNAL_AUDITOR,
        GrcRole.PLANT_MANAGER,
    }
    write_roles = {GrcRole.SUPER_ADMIN, GrcRole.COMPLIANCE_OFFICER}

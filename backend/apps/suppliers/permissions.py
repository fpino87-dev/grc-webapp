"""RBAC modulo Suppliers (newfix F1)."""
from apps.auth_grc.models import GrcRole
from core.permissions import RoleScopedPermission


_GOVERNANCE = {
    GrcRole.SUPER_ADMIN,
    GrcRole.COMPLIANCE_OFFICER,
    GrcRole.RISK_MANAGER,
    GrcRole.PLANT_MANAGER,
}


class SupplierPermission(RoleScopedPermission):
    """Solo governance scrive sui fornitori (assessment, NDA, classificazione
    NIS2). Auditor leggono per evidence."""
    read_roles = _GOVERNANCE | {GrcRole.INTERNAL_AUDITOR, GrcRole.EXTERNAL_AUDITOR}
    write_roles = _GOVERNANCE

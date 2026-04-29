"""RBAC modulo Audit Preparation (newfix F1)."""
from apps.auth_grc.models import GrcRole
from core.permissions import RoleScopedPermission


_AUDITOR_PLUS = {
    GrcRole.SUPER_ADMIN,
    GrcRole.COMPLIANCE_OFFICER,
    GrcRole.INTERNAL_AUDITOR,
    GrcRole.EXTERNAL_AUDITOR,
    GrcRole.RISK_MANAGER,
}


class AuditPrepPermission(RoleScopedPermission):
    """Solo chi prepara/consuma audit. Scrittura ulteriormente ristretta
    per impedire all'external_auditor (osservatore) di modificare evidenze."""
    read_roles = _AUDITOR_PLUS
    write_roles = {
        GrcRole.SUPER_ADMIN,
        GrcRole.COMPLIANCE_OFFICER,
        GrcRole.INTERNAL_AUDITOR,
    }

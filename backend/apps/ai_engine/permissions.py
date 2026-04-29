"""RBAC modulo AI Engine (newfix F1)."""
from apps.auth_grc.models import GrcRole
from core.permissions import RoleScopedPermission


class AiEnginePermission(RoleScopedPermission):
    """L'AI Engine produce suggerimenti e applica modifiche su entita'
    sensibili: limitiamo l'accesso ai ruoli con responsabilita' GRC."""
    read_roles = {
        GrcRole.SUPER_ADMIN,
        GrcRole.COMPLIANCE_OFFICER,
        GrcRole.RISK_MANAGER,
        GrcRole.PLANT_MANAGER,
    }
    write_roles = read_roles

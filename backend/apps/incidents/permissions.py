"""RBAC modulo Incidents NIS2 (newfix F1)."""
from apps.auth_grc.models import GrcRole
from core.permissions import RoleScopedPermission


_OPERATIONAL = {
    GrcRole.SUPER_ADMIN,
    GrcRole.COMPLIANCE_OFFICER,
    GrcRole.RISK_MANAGER,
    GrcRole.PLANT_MANAGER,
}

_AUDIT = {GrcRole.INTERNAL_AUDITOR, GrcRole.EXTERNAL_AUDITOR}


class IncidentPermission(RoleScopedPermission):
    """Operativi + auditor leggono; modifica solo agli operativi."""
    read_roles = _OPERATIONAL | _AUDIT
    write_roles = _OPERATIONAL


class NIS2ConfigurationPermission(RoleScopedPermission):
    """Configurazione NIS2: lettura allargata, scrittura solo
    super_admin/compliance_officer."""
    read_roles = _OPERATIONAL | _AUDIT
    write_roles = {GrcRole.SUPER_ADMIN, GrcRole.COMPLIANCE_OFFICER}

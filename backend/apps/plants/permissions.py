"""RBAC modulo Plant Registry (M01) — P1-3 SoD write-authorization."""
from apps.auth_grc.models import GrcRole
from core.permissions import RoleScopedPermission

_ALL = set(GrcRole.values)


class PlantPermission(RoleScopedPermission):
    """Anagrafica stabilimenti: lettura per tutti i ruoli GRC, modifica ai soli
    super_admin/compliance_officer/plant_manager (registro di compliance)."""
    read_roles = _ALL
    write_roles = {GrcRole.SUPER_ADMIN, GrcRole.COMPLIANCE_OFFICER, GrcRole.PLANT_MANAGER}


class PlantConfigPermission(RoleScopedPermission):
    """Business Unit e attivazione framework: configurazione org-level →
    scrittura solo super_admin/compliance_officer."""
    read_roles = _ALL
    write_roles = {GrcRole.SUPER_ADMIN, GrcRole.COMPLIANCE_OFFICER}

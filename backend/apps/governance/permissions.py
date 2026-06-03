"""RBAC modulo Governance & Ruoli (M00) — P1-3 SoD write-authorization."""
from apps.auth_grc.models import GrcRole
from core.permissions import RoleScopedPermission

_ALL = set(GrcRole.values)


class GovernancePermission(RoleScopedPermission):
    """Assegnazioni ruolo, comitato sicurezza, policy workflow documentale:
    materia di governance → lettura per tutti, scrittura solo
    super_admin/compliance_officer (separazione dei compiti su chi assegna ruoli)."""
    read_roles = _ALL
    write_roles = {GrcRole.SUPER_ADMIN, GrcRole.COMPLIANCE_OFFICER}

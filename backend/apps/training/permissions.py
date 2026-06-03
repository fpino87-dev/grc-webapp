"""RBAC modulo Training (M15) — P1-3 SoD write-authorization."""
from apps.auth_grc.models import GrcRole
from core.permissions import RoleScopedPermission

_ALL = set(GrcRole.values)


class TrainingPermission(RoleScopedPermission):
    """Corsi/iscrizioni/simulazioni phishing: lettura per tutti, gestione
    (creazione corsi, iscrizioni, campagne) ai ruoli di governance formazione."""
    read_roles = _ALL
    write_roles = {GrcRole.SUPER_ADMIN, GrcRole.COMPLIANCE_OFFICER, GrcRole.PLANT_MANAGER}

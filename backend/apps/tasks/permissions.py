"""RBAC modulo Task Management (M08) — P1-3 SoD write-authorization."""
from apps.auth_grc.models import GrcRole
from core.permissions import RoleScopedPermission

_ALL = set(GrcRole.values)
_AUDIT = {GrcRole.INTERNAL_AUDITOR, GrcRole.EXTERNAL_AUDITOR}


class TaskPermission(RoleScopedPermission):
    """Task e checklist operative: lettura per tutti i ruoli; scrittura ai ruoli
    operativi (i destinatari completano task/checklist), auditor esclusi."""
    read_roles = _ALL
    write_roles = _ALL - _AUDIT


class KpiConfigPermission(RoleScopedPermission):
    """Definizioni KPI: configurazione del monitoraggio → scrittura ristretta
    a super_admin/compliance_officer. Snapshot/lettura aperti a tutti."""
    read_roles = _ALL
    write_roles = {GrcRole.SUPER_ADMIN, GrcRole.COMPLIANCE_OFFICER}

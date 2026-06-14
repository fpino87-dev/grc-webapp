"""RBAC modulo Training (M15) — P1-3 SoD write-authorization."""
from apps.auth_grc.models import GrcRole
from core.permissions import RoleScopedPermission

_ALL = set(GrcRole.values)
_GOVERNANCE = {GrcRole.SUPER_ADMIN, GrcRole.COMPLIANCE_OFFICER, GrcRole.PLANT_MANAGER}


class TrainingPermission(RoleScopedPermission):
    """Catalogo corsi: lettura per tutti i ruoli (è materiale informativo),
    gestione (creazione/modifica corsi) ai ruoli di governance formazione."""
    read_roles = _ALL
    write_roles = _GOVERNANCE


class TrainingResultsPermission(RoleScopedPermission):
    """Iscrizioni e risultati phishing: contengono dati personali/performance
    del singolo dipendente (chi ha cliccato, punteggi, esiti). Lettura ristretta
    a governance + auditor interno (GDPR — minimizzazione); esclusi auditor
    esterni e ruoli operativi. Scrittura ai soli ruoli di governance."""
    read_roles = _GOVERNANCE | {GrcRole.INTERNAL_AUDITOR}
    write_roles = _GOVERNANCE

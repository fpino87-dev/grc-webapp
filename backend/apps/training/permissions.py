"""RBAC modulo Training (M15)."""
from apps.auth_grc.models import GrcRole
from core.permissions import RoleScopedPermission, user_has_any_role

_ALL = set(GrcRole.values)
_GOVERNANCE = {GrcRole.SUPER_ADMIN, GrcRole.COMPLIANCE_OFFICER, GrcRole.PLANT_MANAGER}
_SAFE = ("GET", "HEAD", "OPTIONS")


def _is_manager(user) -> bool:
    from .services import is_training_manager

    return is_training_manager(user)


class TrainingPermission(RoleScopedPermission):
    """Catalogo corsi: lettura per tutti i ruoli (è materiale informativo),
    gestione ai ruoli di governance formazione e al CISO nominato."""
    read_roles = _ALL
    write_roles = _GOVERNANCE

    def has_permission(self, request, view) -> bool:
        return super().has_permission(request, view) or (
            request.method not in _SAFE and _is_manager(request.user)
        )


class TrainingRecordsPermission(RoleScopedPermission):
    """Gruppi, piani ed erogazioni: solo conteggi e file di prova, nessun dato
    personale → leggibili anche dagli auditor (sono l'evidenza che cercano).
    Scrittura ai gestori della formazione (ruoli di governance o CISO nominato);
    il perimetro del sito si verifica nei servizi."""
    read_roles = _GOVERNANCE | {GrcRole.INTERNAL_AUDITOR, GrcRole.EXTERNAL_AUDITOR}
    write_roles = _GOVERNANCE

    def has_permission(self, request, view) -> bool:
        user = request.user
        if request.method in _SAFE:
            return user_has_any_role(user, self.read_roles) or _is_manager(user)
        return _is_manager(user)


class TrainingResultsPermission(RoleScopedPermission):
    """Vecchie iscrizioni e risultati phishing per persona (in sola lettura fino
    alla rimozione): dati personali → governance + auditor interno."""
    read_roles = _GOVERNANCE | {GrcRole.INTERNAL_AUDITOR}
    write_roles = _GOVERNANCE

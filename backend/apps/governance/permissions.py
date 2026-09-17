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


class SecurityObjectivePermission(RoleScopedPermission):
    """Obiettivi di sicurezza (§6.2).

    Lettura per tutti i ruoli, auditor esterno compreso: gli obiettivi sono
    evidenza d'audit, ed è esattamente ciò che un auditor chiede di vedere.
    Scrittura a chi governa il SGSI — gli obiettivi sono un impegno della
    direzione, non una configurazione operativa.

    Eccezione sulla registrazione di una misura: la fa chi ha il numero in
    mano (plant manager, control owner), non chi ha fissato il traguardo.
    """

    read_roles = _ALL
    write_roles = {GrcRole.SUPER_ADMIN, GrcRole.COMPLIANCE_OFFICER, GrcRole.RISK_MANAGER}
    measure_roles = write_roles | {GrcRole.PLANT_MANAGER, GrcRole.CONTROL_OWNER}

    def has_permission(self, request, view):
        if getattr(view, "action", None) == "measure":
            from core.permissions import user_has_any_role

            return user_has_any_role(request.user, self.measure_roles)
        return super().has_permission(request, view)

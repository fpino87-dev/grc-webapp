"""RBAC modulo Management Review (newfix F1)."""
from apps.auth_grc.models import GrcRole
from core.permissions import RoleScopedPermission


class ManagementReviewPermission(RoleScopedPermission):
    """ISO 27001 clausola 9.3: la revisione direzione coinvolge top management
    e auditor. Scrittura ristretta a CISO/Compliance Officer."""
    read_roles = {
        GrcRole.SUPER_ADMIN,
        GrcRole.COMPLIANCE_OFFICER,
        GrcRole.RISK_MANAGER,
        GrcRole.INTERNAL_AUDITOR,
        GrcRole.PLANT_MANAGER,
    }
    write_roles = {GrcRole.SUPER_ADMIN, GrcRole.COMPLIANCE_OFFICER}


class ReviewWithBodyMembersPermission(ManagementReviewPermission):
    """Solo per la viewset dei riesami, il cui queryset per i non-ruoli è
    ristretto ai riesami del proprio organo. NON usarla su decisioni e ordine
    del giorno: lì il queryset è filtrato solo per sito."""

    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        if super().has_permission(request, view):
            return True
        # Un componente in carica di un organo di governo con account (es. un
        # consigliere) legge e approva i riesami del proprio organo, anche
        # senza un ruolo GRC di lettura. Il queryset lo restringe a quelli;
        # nessun'altra scrittura gli è consentita.
        action = getattr(view, "action", None)
        if request.method in ("GET", "HEAD", "OPTIONS") or action == "approve":
            from apps.governance.services import user_committee_ids

            return bool(user_committee_ids(request.user))
        return False

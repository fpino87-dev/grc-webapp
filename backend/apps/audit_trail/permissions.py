"""Permessi RBAC per il modulo M10 Audit Trail.

Lettura: SUPER_ADMIN, COMPLIANCE_OFFICER, INTERNAL_AUDITOR, EXTERNAL_AUDITOR.
Verifica integrità: solo SUPER_ADMIN, COMPLIANCE_OFFICER (operazione costosa
e a contenuto sensibile).

Plant Manager NON ha accesso: l'audit log è cross-plant e contiene metadata
su tutte le azioni della piattaforma.
"""
from __future__ import annotations

from rest_framework.permissions import BasePermission

from apps.auth_grc.models import GrcRole, UserPlantAccess


_READ_ROLES = frozenset({
    GrcRole.SUPER_ADMIN,
    GrcRole.COMPLIANCE_OFFICER,
    GrcRole.INTERNAL_AUDITOR,
    GrcRole.EXTERNAL_AUDITOR,
})

_INTEGRITY_ROLES = frozenset({
    GrcRole.SUPER_ADMIN,
    GrcRole.COMPLIANCE_OFFICER,
})


def _user_has_any_role(user, allowed: frozenset) -> bool:
    if user is None or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    return UserPlantAccess.objects.filter(
        user=user, role__in=allowed, deleted_at__isnull=True,
    ).exists()


class AuditLogReadPermission(BasePermission):
    """Solo CISO/Compliance/Auditor può leggere l'audit log."""

    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        return _user_has_any_role(request.user, _READ_ROLES)


class AuditLogIntegrityPermission(BasePermission):
    """Solo SUPER_ADMIN/CISO può eseguire la verifica di integrità."""

    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        return _user_has_any_role(request.user, _INTEGRITY_ROLES)

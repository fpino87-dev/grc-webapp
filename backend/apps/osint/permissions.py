"""Permessi RBAC per il modulo OSINT.

Lettura: SUPER_ADMIN, COMPLIANCE_OFFICER, RISK_MANAGER, INTERNAL_AUDITOR,
         EXTERNAL_AUDITOR. Plant Manager riceve l'accesso in lettura solo se
         ha membership attiva (qualsiasi plant — il modulo è cross-plant).
Scrittura (settings, escalate, classifica sottodomini, force-scan):
         SUPER_ADMIN, COMPLIANCE_OFFICER, RISK_MANAGER.
"""
from __future__ import annotations

from rest_framework.permissions import BasePermission

from apps.auth_grc.models import GrcRole, UserPlantAccess

_READ_ROLES = frozenset({
    GrcRole.SUPER_ADMIN,
    GrcRole.COMPLIANCE_OFFICER,
    GrcRole.RISK_MANAGER,
    GrcRole.INTERNAL_AUDITOR,
    GrcRole.EXTERNAL_AUDITOR,
    GrcRole.PLANT_MANAGER,
})

_WRITE_ROLES = frozenset({
    GrcRole.SUPER_ADMIN,
    GrcRole.COMPLIANCE_OFFICER,
    GrcRole.RISK_MANAGER,
})


def _user_has_any_role(user, allowed: frozenset) -> bool:
    if user is None or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    return UserPlantAccess.objects.filter(user=user, role__in=allowed).exists()


class OsintReadPermission(BasePermission):
    """Lettura modulo OSINT — ruoli compliance/risk/audit/plant manager."""

    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        return _user_has_any_role(request.user, _READ_ROLES)


class OsintWritePermission(BasePermission):
    """Scrittura modulo OSINT — solo ruoli con responsabilità di compliance/risk."""

    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return _user_has_any_role(request.user, _READ_ROLES)
        return _user_has_any_role(request.user, _WRITE_ROLES)

"""Permessi RBAC per il Centro Operativo (M21).

Il Centro aggrega postura di sicurezza interna (incl. esposizione OSINT, gap,
config mancanti): è informazione **interna**. L'`EXTERNAL_AUDITOR` è escluso
(coerente col vincolo "notifiche/esposizione solo a personale interno").
"""
from __future__ import annotations

from rest_framework.permissions import BasePermission

from apps.auth_grc.models import GrcRole, UserPlantAccess

_READ_ROLES = frozenset({
    GrcRole.SUPER_ADMIN,
    GrcRole.COMPLIANCE_OFFICER,
    GrcRole.RISK_MANAGER,
    GrcRole.INTERNAL_AUDITOR,
    GrcRole.PLANT_MANAGER,
})


class CockpitPermission(BasePermission):
    """Lettura Centro Operativo — ruoli interni con responsabilità GRC."""

    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        user = request.user
        if user is None or not user.is_authenticated:
            return False
        if getattr(user, "is_superuser", False):
            return True
        return UserPlantAccess.objects.filter(user=user, role__in=_READ_ROLES).exists()

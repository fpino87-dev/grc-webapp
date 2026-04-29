"""
Permission RBAC riutilizzabile (newfix F1).

`RoleScopedPermission` consente di mappare un ViewSet a uno o piu' ruoli
GRC sia per la lettura sia per la scrittura, sostituendo `IsAuthenticated`
con un controllo per-ruolo coerente con il pattern OSINT (`OsintReadPermission`/
`OsintWritePermission`).

Uso tipico:

    class IncidentRead(RoleScopedPermission):
        read_roles  = {GrcRole.SUPER_ADMIN, GrcRole.COMPLIANCE_OFFICER, ...}
        write_roles = {GrcRole.SUPER_ADMIN, GrcRole.COMPLIANCE_OFFICER, ...}

    class IncidentViewSet(...):
        permission_classes = [IncidentRead]

I superuser bypassano sempre il controllo. Gli utenti soft-deleted da
`UserPlantAccess` non contano (filter `deleted_at__isnull=True`). Lo
scoping per plant resta affidato al `PlantScopedQuerysetMixin` (S1):
questa classe risponde alla domanda "puo' chiamare l'endpoint?", lo
scoping risponde "su quali record?".
"""
from __future__ import annotations

from typing import Iterable

from rest_framework.permissions import BasePermission

from apps.auth_grc.models import UserPlantAccess


_SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


def user_has_any_role(user, allowed: Iterable[str]) -> bool:
    """True se `user` ha almeno un `UserPlantAccess` attivo con ruolo in
    `allowed`. Superuser sempre True. Utente non autenticato sempre False.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    allowed = frozenset(allowed)
    if not allowed:
        return False
    return UserPlantAccess.objects.filter(
        user=user, role__in=allowed, deleted_at__isnull=True,
    ).exists()


class RoleScopedPermission(BasePermission):
    """
    Permission base configurabile via attributi di classe `read_roles` e
    `write_roles`. Sottoclassare per mapping per modulo:

        class XRead(RoleScopedPermission):
            read_roles = {...}
            write_roles = {...}

    Se `write_roles` e' vuoto/None, la scrittura e' consentita ai soli ruoli
    di lettura (comportamento read-mostly).
    """

    read_roles: Iterable[str] = ()
    write_roles: Iterable[str] = ()

    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        if request.method in _SAFE_METHODS:
            return user_has_any_role(request.user, self.read_roles)
        write = self.write_roles or self.read_roles
        return user_has_any_role(request.user, write)

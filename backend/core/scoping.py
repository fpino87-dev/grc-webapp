"""
Multi-tenancy / RBAC scoping per ViewSet (CLAUDE.md regola #7, fix newfix.md S1).

Filtra automaticamente i queryset in base agli `UserPlantAccess` dell'utente che
fa la richiesta, in modo che un Plant Manager dello stabilimento A non possa
listare/leggere oggetti di Plant B aggirando il client.

Regole di scoping:
  * utente non autenticato → queryset vuoto
  * `is_superuser=True` → nessun filtro (Django superuser di rescue)
  * `UserPlantAccess.scope_type='org'` su almeno un ruolo → nessun filtro
    (es. CISO/Compliance Officer hanno visibilità globale)
  * `scope_type='bu'` → tutti i Plant della BU
  * `scope_type='plant_list' | 'single_plant'` → solo i Plant esplicitamente
    assegnati
  * nessun `UserPlantAccess` attivo → queryset vuoto

Uso:
    class IncidentViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
        queryset = Incident.objects.all()
        serializer_class = IncidentSerializer
        plant_field = "plant"          # default — FK al modello Plant
        allow_null_plant = False       # True se record cross-plant ammessi

`plant_field` può essere un percorso ORM arbitrario:
  * `"plant"`              — FK diretto al Plant (caso più comune)
  * `"plants"`             — M2M al Plant (es. Supplier)
  * `"supplier__plants"`   — via altro modello (es. SupplierAssessment)
Quando il filtro coinvolge join M2M, il queryset risultante riceve `.distinct()`
per evitare righe duplicate.

Note di design:
  * il mixin lavora sul `queryset` ritornato da `super().get_queryset()` —
    rispetta filtri/`select_related` già impostati dal ViewSet.
  * non usa `IsAuthenticated` come permesso: lo scoping si limita a tagliare
    le righe; la negazione 401/403 resta a `permission_classes`.
  * il calcolo `get_user_plant_ids()` è esposto come funzione modulo per
    riuso da parte di altre logiche (es. `services.py` che oggi ricalcolano
    a mano lo stesso filtro).
"""
from __future__ import annotations

from typing import Iterable

from django.db.models import Q, QuerySet


def get_user_plant_ids(user) -> set | None:
    """
    Ritorna l'insieme di Plant.id accessibili dall'utente in base ai suoi
    UserPlantAccess. `None` significa "nessun filtro" (scope org / superuser).
    `set()` vuoto significa "nessun accesso → niente di visibile".
    """
    from apps.auth_grc.models import UserPlantAccess
    from apps.plants.models import Plant

    if user is None or not getattr(user, "is_authenticated", False):
        return set()
    if getattr(user, "is_superuser", False):
        return None

    access_qs = UserPlantAccess.objects.filter(user=user, deleted_at__isnull=True)
    if not access_qs.exists():
        return set()
    if access_qs.filter(scope_type="org").exists():
        return None

    allowed: set = set()
    for access in access_qs.select_related("scope_bu").prefetch_related("scope_plants"):
        if access.scope_type == "bu" and access.scope_bu_id:
            ids = Plant.objects.filter(
                bu_id=access.scope_bu_id, deleted_at__isnull=True,
            ).values_list("id", flat=True)
            allowed.update(ids)
        elif access.scope_type in ("plant_list", "single_plant"):
            ids = access.scope_plants.all().values_list("id", flat=True)
            allowed.update(ids)
    return allowed


class PlantScopedQuerysetMixin:
    """Mixin DRF che restringe `get_queryset()` agli oggetti del plant accessibile.

    Configurabile per-ViewSet:
        plant_field      — nome del FK Plant sul modello (default 'plant')
        allow_null_plant — se True, oggetti senza plant (cross-plant) sono inclusi
    """

    plant_field: str = "plant"
    allow_null_plant: bool = False

    def get_queryset(self) -> QuerySet:  # type: ignore[override]
        qs: QuerySet = super().get_queryset()
        return scope_queryset_by_plant(
            qs,
            self.request.user,
            plant_field=self.plant_field,
            allow_null_plant=self.allow_null_plant,
        )


def scope_queryset_by_plant(
    qs: QuerySet,
    user,
    *,
    plant_field: str = "plant",
    allow_null_plant: bool = False,
    extra_plant_ids: Iterable | None = None,
) -> QuerySet:
    """Versione funzionale del filtro plant — usabile fuori dai ViewSet (services).

    `extra_plant_ids` consente di unire plant aggiuntivi (es. plant del fornitore
    multi-plant) al set calcolato dagli access dell'utente.
    """
    plant_ids = get_user_plant_ids(user)
    if plant_ids is None:
        return qs
    plant_ids = set(plant_ids)
    if extra_plant_ids:
        plant_ids.update(extra_plant_ids)
    if not plant_ids and not allow_null_plant:
        return qs.none()
    flt = Q(**{f"{plant_field}__in": plant_ids})
    if allow_null_plant:
        flt |= Q(**{f"{plant_field}__isnull": True})
    qs = qs.filter(flt)
    # Join via M2M o relazione "to-many" → distinct per evitare duplicati.
    if "__" in plant_field or _is_many_relation(qs.model, plant_field):
        qs = qs.distinct()
    return qs


def _is_many_relation(model, field_name: str) -> bool:
    """True se `field_name` è una relazione many-to-many o reverse."""
    try:
        f = model._meta.get_field(field_name)
    except Exception:
        return False
    return getattr(f, "many_to_many", False) or getattr(f, "one_to_many", False)

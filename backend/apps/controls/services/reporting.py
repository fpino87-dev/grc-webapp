from ..models import ControlInstance
from .evidence import is_covered_by_extender


def _count_effective_by_plant(extra_q) -> dict:
    """Conta per plant i ControlInstance che soddisfano `extra_q`, applicando la
    STESSA deduplicazione della lista controlli (`ControlInstanceViewSet`): solo
    framework attivi del plant + esclusione dei controlli L2 *superseded* da un L3
    (`ControlMapping(extends)`). Così i numeri coincidono con quelli mostrati nel
    modulo Controlli. Ritorna `{plant_id (str): count}` (solo count > 0)."""
    from apps.plants.models import Plant
    from apps.plants.services import get_active_frameworks
    from ..models import ControlMapping

    out: dict[str, int] = {}
    plant_ids = (
        ControlInstance.objects.filter(deleted_at__isnull=True)
        .values_list("plant_id", flat=True).distinct()
    )
    for plant in Plant.objects.filter(pk__in=list(plant_ids), deleted_at__isnull=True):
        active = get_active_frameworks(plant)
        qs = ControlInstance.objects.filter(
            plant=plant, deleted_at__isnull=True, control__framework__in=active,
        ).filter(extra_q)
        if not qs.exists():
            continue
        fw_ids = (
            ControlInstance.objects.filter(plant=plant, deleted_at__isnull=True)
            .values_list("control__framework_id", flat=True).distinct()
        )
        superseded = ControlMapping.objects.filter(
            relationship="extends",
            source_control__framework_id__in=fw_ids,
            target_control__framework_id__in=fw_ids,
        ).values_list("target_control_id", flat=True)
        count = qs.exclude(control_id__in=superseded).count()
        if count > 0:
            out[str(plant.pk)] = count
    return out


def count_open_gaps_by_plant() -> dict:
    """Controlli "aperti" (gap/parziale) per plant — vedi `_count_effective_by_plant`."""
    from django.db.models import Q
    return _count_effective_by_plant(Q(status__in=["gap", "parziale"]))


def count_revaluation_by_plant() -> dict:
    """Controlli da rivalutare (`needs_revaluation=True`) per plant, deduplicati."""
    from django.db.models import Q
    return _count_effective_by_plant(Q(needs_revaluation=True))


def get_compliance_summary(plant_id, framework_code=None):
    """
    % di compliance del plant (per framework specifico o globale sui framework
    attivi).

    Regole:
    - I controlli `na` (Non Applicabile) sono fuori contesto organizzativo e
      vengono **esclusi dal denominatore** (non sono ne' gap ne' compliant —
      non li valutiamo affatto).
    - I controlli non-compliant ma coperti da un extender (es. TISAX L2 con
      evidenza caricata sul corrispondente L3 via `ControlMapping(extends)`)
      vengono conteggiati come compliant nel numeratore (la regola di
      copertura e' la stessa di `audit_prep.validation` / `is_covered_by_extender`).

    I campi `compliant_direct` e `covered_by_extender` sono esposti
    separatamente per UI esplicative (es. "29 + 12 coperti da L3").
    """
    from django.db.models import Count
    from django.utils import timezone

    from apps.plants.models import Plant
    from apps.plants.services import get_active_frameworks

    qs = ControlInstance.objects.filter(
        plant_id=plant_id,
        deleted_at__isnull=True,
    )
    if framework_code:
        qs = qs.filter(control__framework__code=framework_code)
    else:
        plant = Plant.objects.filter(pk=plant_id).first() if plant_id else None
        active_fws = get_active_frameworks(plant)
        qs = qs.filter(control__framework__in=active_fws)

    na_count = qs.filter(status="na").count()
    qs = qs.exclude(status="na")
    total = qs.count()

    if total == 0:
        return {
            "total": 0,
            "compliant": 0,
            "compliant_direct": 0,
            "covered_by_extender": 0,
            "gap": 0,
            "parziale": 0,
            "non_valutato": 0,
            "na_excluded": na_count,
            "pct_compliant": 0,
        }

    counts = qs.values("status").annotate(n=Count("id"))
    result = {r["status"]: r["n"] for r in counts}
    compliant_direct = result.get("compliant", 0)

    # Conta i non-compliant coperti da un extender (es. TISAX L2 coperto da L3).
    today = timezone.localdate()
    non_compliant_qs = qs.exclude(status="compliant").select_related("control")
    covered_by_extender = 0
    for ci in non_compliant_qs:
        if is_covered_by_extender(ci, today):
            covered_by_extender += 1

    compliant_effective = compliant_direct + covered_by_extender
    return {
        "total": total,
        "compliant": compliant_effective,
        "compliant_direct": compliant_direct,
        "covered_by_extender": covered_by_extender,
        "gap": result.get("gap", 0),
        "parziale": result.get("parziale", 0),
        "non_valutato": result.get("non_valutato", 0),
        "na_excluded": na_count,
        "pct_compliant": round(compliant_effective / total * 100, 1),
    }

from ..models import ControlInstance
from .evidence import _extends_pairs_qs


def _count_effective_by_plant(extra_q) -> dict:
    """Conta per plant i ControlInstance che soddisfano `extra_q`, applicando la
    STESSA deduplicazione della lista controlli (`ControlInstanceViewSet`): solo
    framework attivi del plant + esclusione dei controlli L2 *superseded* da un L3
    (`ControlMapping(extends)`). Così i numeri coincidono con quelli mostrati nel
    modulo Controlli. Ritorna `{plant_id (str): count}` (solo count > 0)."""
    from apps.plants.models import Plant
    from apps.plants.services import get_active_frameworks
    from .evidence import superseded_base_ids

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
        superseded = superseded_base_ids(fw_ids)
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


def count_tisax_missing_implementation_by_plant() -> dict:
    """Controlli TISAX con maturità dichiarata ≥ 3 ma senza "Implementation
    description", per plant, deduplicati come la lista controlli.

    Maturità ≥ 3 replica `ControlInstance.calc_maturity_level` in SQL: override
    manuale ≥ 3, oppure calcolo automatico su stato `compliant` (3 o 4)."""
    from django.db.models import Q
    ml_ge_3 = (
        Q(maturity_level_override=True, maturity_level__gte=3)
        | Q(maturity_level_override=False, status="compliant")
    )
    return _count_effective_by_plant(
        Q(control__framework__code__startswith="TISAX", implementation_description="") & ml_ge_3
    )


# ---------------------------------------------------------------------------
# Percentuale di conformità — regola unica
# ---------------------------------------------------------------------------
# Usata da Reporting, snapshot settimanale, dashboard_summary e Assistente, così
# lo stesso sito/framework dà ovunque lo stesso numero. È la regola dell'elenco
# del modulo Controlli (`ControlInstanceViewSet` senza filtro framework):
# - solo framework attivi sul sito;
# - i controlli base sostituiti da un extender attivo sullo stesso sito
#   (TISAX L2 → VH L3 via `ControlMapping(extends)`) sono fuori conteggio: si
#   valutano sul VH e vengono riportati a parte (`superseded_by_extender`);
# - N/A fuori dal denominatore (riportati in `na_excluded`).

COMPLIANCE_STATUSES = ("compliant", "parziale", "gap", "non_valutato")


def effective_control_rows(plants, framework_codes=None) -> list[dict]:
    """Righe delle istanze di controllo dei `plants` sui framework attivi, con
    il flag `superseded`. Tre query in tutto, indipendentemente dal numero di
    siti. Ogni riga: plant_id, control_id, framework_code, domain_id, status,
    superseded."""
    from apps.plants.models import PlantFramework

    plant_ids = [p.pk if hasattr(p, "pk") else p for p in plants]
    if not plant_ids:
        return []

    pf_qs = PlantFramework.objects.filter(
        plant_id__in=plant_ids,
        active=True,
        deleted_at__isnull=True,
        framework__archived_at__isnull=True,
        framework__deleted_at__isnull=True,
    )
    if framework_codes is not None:
        pf_qs = pf_qs.filter(framework__code__in=list(framework_codes))
    active: dict = {}
    for plant_id, fw_id in pf_qs.values_list("plant_id", "framework_id"):
        active.setdefault(plant_id, set()).add(fw_id)
    if not active:
        return []

    # Il sostituito va calcolato su TUTTI i framework attivi del sito, anche se
    # si chiede un solo framework: L2 perde i controlli coperti da L3 attivo.
    all_active: dict = {}
    for plant_id, fw_id in PlantFramework.objects.filter(
        plant_id__in=list(active),
        active=True,
        deleted_at__isnull=True,
        framework__archived_at__isnull=True,
        framework__deleted_at__isnull=True,
    ).values_list("plant_id", "framework_id"):
        all_active.setdefault(plant_id, set()).add(fw_id)
    all_fw_ids = set().union(*all_active.values())
    extenders_of: dict = {}
    for src_fw, tgt_fw, target in _extends_pairs_qs(all_fw_ids).values_list(
        "source_control__framework_id", "target_control__framework_id", "target_control_id",
    ):
        extenders_of.setdefault(target, []).append((src_fw, tgt_fw))

    wanted_fw_ids = set().union(*active.values())
    rows = []
    for r in ControlInstance.objects.filter(
        plant_id__in=list(active),
        deleted_at__isnull=True,
        control__framework_id__in=wanted_fw_ids,
    ).values(
        "plant_id", "control_id", "status",
        "control__framework_id", "control__framework__code", "control__domain_id",
    ):
        plant_id, fw_id = r["plant_id"], r["control__framework_id"]
        if fw_id not in active.get(plant_id, ()):
            continue
        plant_fws = all_active.get(plant_id, set())
        superseded = any(
            src_fw in plant_fws and tgt_fw in plant_fws
            for src_fw, tgt_fw in extenders_of.get(r["control_id"], ())
        )
        rows.append({
            "plant_id": plant_id,
            "control_id": r["control_id"],
            "framework_code": r["control__framework__code"],
            "domain_id": r["control__domain_id"],
            "status": r["status"],
            "superseded": superseded,
        })
    return rows


def summarize_compliance(rows) -> dict:
    """Conteggi e percentuale di conformità su righe di `effective_control_rows`."""
    counts = dict.fromkeys(COMPLIANCE_STATUSES, 0)
    na = superseded = 0
    for r in rows:
        if r["superseded"]:
            superseded += 1
        elif r["status"] == "na":
            na += 1
        else:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
    total = sum(counts.values())
    return {
        "total": total,
        **counts,
        "na_excluded": na,
        "superseded_by_extender": superseded,
        "pct_compliant": round(counts["compliant"] / total * 100, 1) if total else 0,
    }


def get_compliance_summary(plant_id, framework_code=None):
    """
    % di compliance del sito (per framework o sull'insieme dei framework
    attivi), con la regola unica descritta sopra.

    Chiavi legacy per i consumatori esistenti (Assistente): `compliant_direct`
    coincide con `compliant`; `covered_by_extender` riporta i controlli base
    valutati tramite l'extender (es. i controlli TISAX L2 sostituiti dal VH L3).
    """
    if not plant_id:
        return {**summarize_compliance([]), "compliant_direct": 0, "covered_by_extender": 0}
    rows = effective_control_rows(
        [plant_id], [framework_code] if framework_code else None,
    )
    summary = summarize_compliance(rows)
    return {
        **summary,
        "compliant_direct": summary["compliant"],
        "covered_by_extender": summary["superseded_by_extender"],
    }

"""Scope corrente dei KPI operativi: quali coppie (definizione, sito) sono
legittime con la configurazione attuale delle KPIDefinition.

È la fonte di verità unica per:
  - il fan-out del calcolo settimanale (`compute_operational_kpis`);
  - la pulizia degli snapshot rimasti fuori scope (task, data migration e
    modifiche a una definizione);
  - la scelta dello snapshot da mostrare quando per lo stesso (kpi_code, sito)
    ne esistono più d'uno (lettore del riesame, trend).

Regole (le stesse del fan-out):
  - definizione cancellata o non attiva → nessuna coppia;
  - definizione di sito → solo quel sito;
  - definizione globale → tutti i siti che non hanno una propria definizione
    (anche disattivata) dello stesso kpi_code, più `plant=None` (valori
    globali da ingest API / inserimento manuale).

Le funzioni accettano le classi dei modelli come parametro così la data
migration può passare i modelli storici (`apps.get_model`) e usare la stessa
logica; per questo i filtri su `deleted_at` sono sempre espliciti e non si
affidano al manager soft-delete.
"""
from __future__ import annotations

from django.utils import timezone


def _models():
    from apps.plants.models import Plant

    from .models import KPIDefinition, OperationalKpiSnapshot

    return KPIDefinition, OperationalKpiSnapshot, Plant


def _all_rows(model):
    manager = model.objects
    return manager.all_with_deleted() if hasattr(manager, "all_with_deleted") else manager.all()


def current_scope(kpi_code=None, *, KPIDefinition=None, Plant=None) -> dict:
    """{kpi_definition_id: set(plant_id | None)} delle coppie legittime.

    Le definizioni cancellate o non attive compaiono con un insieme vuoto;
    `kpi_code` restringe il calcolo a un solo codice."""
    if KPIDefinition is None or Plant is None:
        KPIDefinition, _snap, Plant = _models()

    defs = _all_rows(KPIDefinition)
    if kpi_code is not None:
        defs = defs.filter(kpi_code=kpi_code)
    defs = list(defs.values("id", "kpi_code", "plant_id", "is_active", "deleted_at"))

    # Siti con una definizione propria (anche disattivata): la globale non vale lì.
    overridden: dict = {}
    for d in defs:
        if d["plant_id"] is not None and d["deleted_at"] is None:
            overridden.setdefault(d["kpi_code"], set()).add(d["plant_id"])

    all_plants = None
    scope = {}
    for d in defs:
        if d["deleted_at"] is not None or not d["is_active"]:
            scope[d["id"]] = set()
        elif d["plant_id"] is not None:
            scope[d["id"]] = {d["plant_id"]}
        else:
            if all_plants is None:
                all_plants = set(
                    _all_rows(Plant).filter(deleted_at__isnull=True).values_list("id", flat=True)
                )
            scope[d["id"]] = (all_plants - overridden.get(d["kpi_code"], set())) | {None}
    return scope


def in_scope(scope: dict, kpi_definition_id, plant_id) -> bool:
    return plant_id in scope.get(kpi_definition_id, set())


def sync_snapshots_with_scope(
    kpi_code=None, *, KPIDefinition=None, OperationalKpiSnapshot=None, Plant=None,
) -> dict:
    """Allinea gli snapshot allo scope corrente (idempotente):

      - soft-delete degli snapshot vivi fuori scope (definizione disattivata o
        cancellata, sito passato a una definizione propria, cambio di sito);
      - ripristino degli snapshot cancellati tornati in scope (definizione
        riattivata o ripristinata: il trend storico ritorna).

    Soft delete e non DELETE: i valori inseriti a mano o arrivati via API non
    sono ricalcolabili e restano recuperabili. Ritorna i conteggi e, per
    definizione, [tolti, ripristinati]."""
    if KPIDefinition is None or OperationalKpiSnapshot is None or Plant is None:
        KPIDefinition, OperationalKpiSnapshot, Plant = _models()

    scope = current_scope(kpi_code, KPIDefinition=KPIDefinition, Plant=Plant)
    if not scope:
        return {"pruned": 0, "restored": 0, "by_definition": {}}

    base = _all_rows(OperationalKpiSnapshot)
    rows = base.filter(kpi_definition_id__in=list(scope)).values_list(
        "id", "kpi_definition_id", "plant_id", "deleted_at",
    )
    to_prune, to_restore = [], []
    by_definition: dict = {}
    for snap_id, def_id, plant_id, deleted_at in rows:
        legit = plant_id in scope[def_id]
        if deleted_at is None and not legit:
            to_prune.append(snap_id)
            by_definition.setdefault(def_id, [0, 0])[0] += 1
        elif deleted_at is not None and legit:
            to_restore.append(snap_id)
            by_definition.setdefault(def_id, [0, 0])[1] += 1

    now = timezone.now()
    if to_prune:
        base.filter(id__in=to_prune).update(deleted_at=now, updated_at=now)
    if to_restore:
        base.filter(id__in=to_restore).update(deleted_at=None, updated_at=now)
    return {"pruned": len(to_prune), "restored": len(to_restore), "by_definition": by_definition}


def sync_and_log(kpi_code=None, user=None) -> dict:
    """`sync_snapshots_with_scope` con traccia nell'audit trail, una voce per
    definizione toccata (solo conteggi, nessun dato personale)."""
    from core.audit import log_action

    from .services import _resolve_audit_user

    result = sync_snapshots_with_scope(kpi_code)
    if not result["by_definition"]:
        return result
    audit_user = _resolve_audit_user(user)
    if audit_user is None:
        return result
    KPIDefinition, _snap, _plant = _models()
    defs = KPIDefinition.objects.all_with_deleted().filter(pk__in=list(result["by_definition"]))
    for kpi_def in defs:
        pruned, restored = result["by_definition"][kpi_def.pk]
        log_action(
            user=audit_user,
            action_code="kpi_snapshot.scope_synced",
            level="L1",
            entity=kpi_def,
            payload={
                "kpi_code": kpi_def.kpi_code,
                "plant_id": str(kpi_def.plant_id) if kpi_def.plant_id else None,
                "pruned": pruned,
                "restored": restored,
            },
        )
    return result


def pick_snapshot(candidates, scope: dict, viewed_plant_id=None):
    """Fra più snapshot dello stesso KPI per lo stesso sito sceglie quello da
    mostrare. Conta prima la definizione che vale per il sito guardato
    (`viewed_plant_id`, altrimenti il sito dello snapshot), poi la settimana
    più recente, poi il valore del sito rispetto a quello globale, poi uno
    stato misurato rispetto a `no_data`."""
    def rank(s):
        target = viewed_plant_id if viewed_plant_id is not None else s.plant_id
        relevant = in_scope(scope, s.kpi_definition_id, s.plant_id) and in_scope(
            scope, s.kpi_definition_id, target,
        )
        return (relevant, s.week_start, s.plant_id is not None, s.status != "no_data", s.created_at)

    return max(candidates, key=rank) if candidates else None

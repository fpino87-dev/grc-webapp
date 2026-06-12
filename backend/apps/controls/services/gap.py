"""
Gap analysis cross-framework (C12 — SPEC_gap_analysis).

Modello hub-and-spoke: tutte le relazioni cross-framework passano per ISO 27001
(ControlMapping con source ISO e relationship equivalente/parziale/correlato,
caricate da ISO27001.json). I framework non-ISO si collegano tra loro per
transitività sul controllo ISO comune, con credito pari alla relazione più
debole delle due gambe.

Lo stato di un elemento deriva dallo STATUS UFFICIALE dell'istanza (decisione
condivisa con l'utente): dopo C1 lo status è già evidence-gated e validato da
un umano, quindi non si ricalcola dalle evidenze raw. `na` e le esclusioni SoA
escono dal denominatore. Per ACN la copertura si conta sui REQUIREMENT
applicabili al profilo (87 importante / 116 essenziale), che ereditano lo stato
della loro misura (la valutazione M03 vive a livello di ControlInstance).

Il riuso (`*_riuso`) è un credito DA VALIDARE, non conformità certificata: in
UI va presentato come suggerimento di lavoro.
"""
from ..models import Control, ControlInstance, ControlMapping

HUB_CODE = "ISO27001"

# Pseudo-target "TISAX" → framework reali per profilo (spec §3.2)
TISAX_PROFILES = {
    "AL2": ["TISAX_L2"],
    "AL3": ["TISAX_L2", "TISAX_L3"],
}

VALID_TARGETS = {"ISO27001", "NIS2", "ACN_NIS2", "TISAX"}

# Forza della relazione: per la transitività vale la gamba più debole (spec §4.2)
_REL_STRENGTH = {"correlato": 0, "parziale": 1, "equivalente": 2}

# Pesi per la copertura assistita (spec §6, configurabili)
WEIGHT_EQUIVALENTE = 1.0
WEIGHT_PARZIALE = 0.5

STATE_COPERTO = "coperto"
STATE_COPERTO_RIUSO = "coperto_riuso"
STATE_PARZIALE = "parziale"
STATE_PARZIALE_RIUSO = "parziale_riuso"
STATE_SCOPERTO = "scoperto"
STATE_ESCLUSO = "escluso"


def _weakest(rel_a: str, rel_b: str) -> str:
    return rel_a if _REL_STRENGTH[rel_a] <= _REL_STRENGTH[rel_b] else rel_b


def _direct_state(instance) -> str:
    """Mappa lo status ufficiale dell'istanza sullo stato gap-analysis."""
    if instance is None:
        return STATE_SCOPERTO
    if instance.status == "na":
        return STATE_ESCLUSO
    if instance.applicability == "escluso":  # esclusione SoA (ISO)
        return STATE_ESCLUSO
    if instance.status == "compliant":
        return STATE_COPERTO
    if instance.status == "parziale":
        return STATE_PARZIALE
    return STATE_SCOPERTO  # gap / non_valutato


def _requirement_applicable(req: dict, profile: str) -> bool:
    """Profilo ACN: 'importante' tiene i requirement con 'important' in
    applies_to (un requirement senza applies_to vale per tutti); 'essenziale'
    li tiene tutti. Stessa regola del drawer (detail-info)."""
    if profile != "importante":
        return True
    applies_to = req.get("applies_to") or []
    return not applies_to or "important" in applies_to


def _req_text(req: dict, lang: str) -> str:
    tr = req.get("translations") or {}
    loc = tr.get(lang) or tr.get("it") or {}
    return (loc.get("text") if isinstance(loc, dict) else "") or ""


def run_gap_analysis(
    target: str,
    plant,
    profile: str = "",
    include_proto: bool = False,
    lang: str = "it",
) -> dict:
    """Gap analysis del plant rispetto a `target` (+ profilo dove previsto).

    Restituisce items con stato finale, cross-link verso le controparti dei
    framework collegati (sempre visibili, anche se la controparte non è
    compliant — su richiesta utente) e aggregati di copertura diretta/assistita
    per dominio.
    """
    # ── Set di controlli applicabili ─────────────────────────────────────────
    if target == "TISAX":
        profile = profile if profile in TISAX_PROFILES else "AL2"
        fw_codes = list(TISAX_PROFILES[profile])
        if include_proto:
            fw_codes.append("TISAX_PROTO")
    else:
        fw_codes = [target]
        if target == "ACN_NIS2" and profile not in ("importante", "essenziale"):
            # default dal sito: importante→importante, altrimenti vista completa
            profile = "importante" if plant.nis2_scope == "importante" else "essenziale"

    controls = list(
        Control.objects.filter(
            framework__code__in=fw_codes, deleted_at__isnull=True,
        ).select_related("framework", "domain").order_by("framework__code", "external_id")
    )

    # ── Stato per controllo: istanze del plant (tutte, una query) ────────────
    instances = {
        ci.control_id: ci
        for ci in ControlInstance.objects.filter(
            plant=plant, deleted_at__isnull=True,
        ).only("control_id", "status", "applicability")
    }

    # ── Mapping hub ISO (una query) + extends TISAX ──────────────────────────
    hub_qs = ControlMapping.objects.filter(
        source_control__framework__code=HUB_CODE,
        relationship__in=("equivalente", "parziale", "correlato"),
        deleted_at__isnull=True,
        source_control__deleted_at__isnull=True,
        target_control__deleted_at__isnull=True,
    ).select_related(
        "source_control__framework", "target_control__framework",
    )
    hub_by_source: dict = {}   # iso_control_id -> [(target_control, rel)]
    hub_by_target: dict = {}   # target_control_id -> [(iso_control, rel)]
    for m in hub_qs:
        hub_by_source.setdefault(m.source_control_id, []).append((m.target_control, m.relationship))
        hub_by_target.setdefault(m.target_control_id, []).append((m.source_control, m.relationship))

    # extends: L3-VH (source) -> L2 base (target). Serve in due direzioni:
    # lo stato del base eredita dal VH (superseded in M03) e il VH eredita i
    # cross-link del base (il crosswalk punta sempre agli ID L2).
    extends = list(
        ControlMapping.objects.filter(
            relationship="extends", deleted_at__isnull=True,
            source_control__deleted_at__isnull=True,
            target_control__deleted_at__isnull=True,
        ).only("source_control_id", "target_control_id")
    )
    extender_of_base = {m.target_control_id: m.source_control_id for m in extends}
    base_of_extender = {m.source_control_id: m.target_control_id for m in extends}

    def best_instance(control_id):
        """Istanza del controllo; per i base L2 estesi da un VH, quando il VH è
        stato valutato è LUI l'istanza autoritativa (dedup M03: si valuta il
        VH, il base è superseded) — anche per 'na', che nell'ordine di stato
        vale 0 e altrimenti perderebbe contro gap/non_valutato del base."""
        own = instances.get(control_id)
        ext_id = extender_of_base.get(control_id)
        ext = instances.get(ext_id) if ext_id else None
        if own is None:
            return ext
        if ext is None:
            return own
        return ext if ext.status != "non_valutato" else own

    def counterpart_status(control_id):
        ci = best_instance(control_id)
        return ci.status if ci else None

    # ── Cross-link e credito di riuso per un controllo target ────────────────
    def build_cross(control: Control) -> list[dict]:
        """Controparti collegate via hub ISO. Sempre incluse (anche non
        compliant: l'utente vuole vedere il legame); le transitive solo se
        hanno un'istanza sul plant (altrimenti è rumore non azionabile)."""
        out = []
        seen = set()

        def add(ctrl, rel, via=None, require_instance=False):
            if ctrl.pk == control.pk or ctrl.pk in seen:
                return
            status = counterpart_status(ctrl.pk)
            if require_instance and status is None:
                return
            seen.add(ctrl.pk)
            out.append({
                "framework": ctrl.framework.code,
                "external_id": ctrl.external_id,
                "title": ctrl.get_title(lang),
                "relationship": rel,
                "status": status,
                "via": via,
            })

        # il VH eredita i cross-link del base L2 (il crosswalk punta al base)
        lookup_ids = [control.pk]
        base_id = base_of_extender.get(control.pk)
        if base_id:
            lookup_ids.append(base_id)

        if control.framework.code == HUB_CODE:
            for tgt, rel in hub_by_source.get(control.pk, []):
                add(tgt, rel)
        else:
            for cid in lookup_ids:
                for iso_ctrl, rel1 in hub_by_target.get(cid, []):
                    add(iso_ctrl, rel1)
                    for other, rel2 in hub_by_source.get(iso_ctrl.pk, []):
                        if other.framework.code in fw_codes:
                            continue  # stesso target (o stesso profilo TISAX)
                        add(other, _weakest(rel1, rel2),
                            via=iso_ctrl.external_id, require_instance=True)
        # compliant prima, poi per forza di relazione
        out.sort(key=lambda c: (c["status"] != "compliant", -_REL_STRENGTH[c["relationship"]]))
        return out

    def apply_reuse(state: str, cross: list[dict]) -> str:
        """Upgrade dello stato con il credito delle controparti compliant
        (equivalente→coperto_riuso, parziale→parziale_riuso, correlato mai)."""
        if state not in (STATE_SCOPERTO, STATE_PARZIALE):
            return state
        rels = {c["relationship"] for c in cross if c["status"] == "compliant"}
        if "equivalente" in rels:
            return STATE_COPERTO_RIUSO
        if "parziale" in rels and state == STATE_SCOPERTO:
            return STATE_PARZIALE_RIUSO
        return state

    # ── Costruzione items ─────────────────────────────────────────────────────
    items = []
    for control in controls:
        ci = best_instance(control.pk)
        state = _direct_state(ci)
        cross = build_cross(control)
        final_state = apply_reuse(state, cross)

        entry = {
            "id": str(control.pk),
            "external_id": control.external_id,
            "framework": control.framework.code,
            "title": control.get_title(lang),
            "domain": control.domain.code if control.domain else "",
            "domain_name": control.domain.get_name(lang) if control.domain else "",
            "direct_status": ci.status if ci else None,
            "state": final_state,
            "cross": cross,
            "weight": 1,
        }

        if target == "ACN_NIS2":
            reqs = [r for r in (control.requirements or []) if _requirement_applicable(r, profile)]
            if not reqs:
                continue  # misura senza requirement applicabili al profilo
            entry["weight"] = len(reqs)
            entry["requirements"] = [
                {
                    "punto": r.get("punto", ""),
                    "applies_to": r.get("applies_to") or [],
                    "text": _req_text(r, lang),
                }
                for r in reqs
            ]

        items.append(entry)

    # ── Aggregati (pesati sui requirement per ACN) ────────────────────────────
    counts = {s: 0 for s in (
        STATE_COPERTO, STATE_COPERTO_RIUSO, STATE_PARZIALE,
        STATE_PARZIALE_RIUSO, STATE_SCOPERTO, STATE_ESCLUSO,
    )}
    by_domain: dict[str, dict] = {}
    for e in items:
        counts[e["state"]] += e["weight"]
        d = by_domain.setdefault(e["domain"], {
            "code": e["domain"], "name": e["domain_name"],
            **{s: 0 for s in counts},
        })
        d[e["state"]] += e["weight"]

    def _coverage(c: dict) -> dict:
        applicable = sum(c[s] for s in counts if s != STATE_ESCLUSO)
        if not applicable:
            return {"applicable": 0, "direct_pct": 0.0, "assisted_pct": 0.0}
        direct = c[STATE_COPERTO]
        assisted = (
            direct
            + WEIGHT_EQUIVALENTE * c[STATE_COPERTO_RIUSO]
            + WEIGHT_PARZIALE * (c[STATE_PARZIALE] + c[STATE_PARZIALE_RIUSO])
        )
        return {
            "applicable": applicable,
            "direct_pct": round(direct / applicable * 100, 1),
            "assisted_pct": round(assisted / applicable * 100, 1),
        }

    return {
        "target": target,
        "profile": profile,
        "include_proto": include_proto if target == "TISAX" else None,
        "frameworks": fw_codes,
        "counts": counts,
        "coverage": _coverage(counts),
        "coverage_by_domain": [
            {**d, **_coverage(d)} for d in by_domain.values() if d["code"]
        ],
        "items": items,
    }

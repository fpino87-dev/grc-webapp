"""Centro Operativo (M21) — modello Insight + registry advisor.

Un *advisor* è una funzione `fn(context) -> list[Insight]` che ciascun modulo
registra (decoratore `@register_advisor`). Il Centro Operativo li raccoglie,
classifica e li espone in una vista unica: NON ricalcola la detection, riusa i
service esistenti dei moduli.

Scelta i18n: l'advisor NON produce prosa localizzata. Emette un `code` stabile +
`params` (conteggi/nomi) + metadati (severità, riferimenti, deep-link); la UI
rende i testi via chiavi `cockpit.insights.<code>.*` nelle 5 lingue. Così non si
duplica testo multilingua nel backend e ogni insight resta tracciabile al codice.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import asdict, dataclass, field
from typing import Callable

logger = logging.getLogger(__name__)

# Ordine di gravità per il sort (0 = più urgente).
SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


@dataclass
class AdvisorContext:
    """Contesto passato a ogni advisor. `plant` opzionale per lo scope per-plant."""
    plant: object | None = None
    user: object | None = None


# Aree della postura operativa (per il Posture Score e i filtri UI).
AREAS: tuple[str, ...] = (
    "governance", "controls", "risk", "incidents", "supply_chain", "technical", "continuity",
)


@dataclass
class Insight:
    code: str                       # stabile, es. "osint.key_invalid"
    module: str                     # modulo di origine
    severity: str                   # critical | warning | info
    area: str = "governance"        # una di AREAS — per Posture Score e filtri
    action_type: str = "navigate"   # navigate | ai_assisted | auto_fixable (v1: navigate)
    plant_id: str | None = None     # None = globale/org
    entity_ref: dict | None = None  # {type, id, deep_link}
    params: dict = field(default_factory=dict)          # interpolazione i18n UI
    compliance_refs: list = field(default_factory=list)  # [{framework, control}]
    effort_h: float | None = None
    deadline: str | None = None     # ISO date, opzionale → alza l'urgenza
    owner_role: str = ""

    @property
    def fingerprint(self) -> str:
        """Identità stabile (code + plant + entità) per dedup / snooze / accepted."""
        ref = ""
        if self.entity_ref:
            ref = f"{self.entity_ref.get('type', '')}:{self.entity_ref.get('id', '')}"
        raw = f"{self.code}|{self.plant_id or ''}|{ref}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["fingerprint"] = self.fingerprint
        return d


# Registry -------------------------------------------------------------------

_ADVISORS: list[Callable] = []
_LOADED = False

# Moduli che definiscono advisor — importati una volta per popolare il registry.
# Aggiungere qui il modulo `advisors` di ogni nuovo modulo che espone insight.
_ADVISOR_MODULES: tuple[str, ...] = (
    "apps.cockpit.advisors_builtin",
    "apps.osint.advisors",
)


def register_advisor(fn: Callable) -> Callable:
    """Decoratore: registra una funzione advisor `fn(context) -> list[Insight]`."""
    if fn not in _ADVISORS:
        _ADVISORS.append(fn)
    return fn


def _ensure_loaded() -> None:
    global _LOADED
    if _LOADED:
        return
    import importlib
    for mod in _ADVISOR_MODULES:
        try:
            importlib.import_module(mod)
        except Exception as exc:  # noqa: BLE001 - un advisor rotto non blocca il Centro
            logger.warning("Cockpit: impossibile caricare advisor %s: %s", mod, exc)
    _LOADED = True


def collect_insights(context: "AdvisorContext | None" = None) -> list[Insight]:
    """Esegue tutti gli advisor registrati e ritorna gli insight ordinati per gravità.

    Ogni advisor è isolato: un'eccezione viene loggata, non propaga (un modulo
    rotto non deve oscurare gli insight degli altri)."""
    _ensure_loaded()
    context = context or AdvisorContext()
    out: list[Insight] = []
    for fn in _ADVISORS:
        try:
            produced = fn(context) or []
            out.extend(produced)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cockpit advisor %s ha sollevato: %s", getattr(fn, "__name__", fn), exc)
    out.sort(key=lambda i: SEVERITY_ORDER.get(i.severity, 9))
    return out

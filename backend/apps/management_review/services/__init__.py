"""
Servizi del modulo Revisione di Direzione (M13), organizzati per area:

- review.py   — ciclo di vita: creazione con ordine del giorno §9.3.2, partecipanti,
                decisioni con task/PDCA collegati, chiusura e approvazione
- snapshot.py — dati congelati per la riunione (compliance, documenti, rischi,
                incidenti, PDCA/task, KPI, audit, azioni precedenti, siti)
- summary.py  — sintesi executive con bozza IA (M20) e accettazione umana

L'API pubblica resta `apps.management_review.services.<funzione>`.
"""

from .review import (
    MINUTES_FIELDS,
    add_agenda_item,
    approve_review,
    complete_review,
    create_review,
    create_review_action,
    delete_agenda_item,
    delete_review_action,
    ensure_iso_agenda,
    start_review,
    suggest_chair,
    uncovered_mandatory_items,
    update_agenda_item,
    update_review,
    update_review_action,
)
from .snapshot import (
    SNAPSHOT_LIST_LIMIT,
    generate_snapshot,
    get_kpi_snapshot,
    get_operational_kpi_summary,
)
from .summary import (
    accept_executive_summary,
    discard_summary_draft,
    draft_executive_summary,
)

__all__ = [
    "MINUTES_FIELDS", "SNAPSHOT_LIST_LIMIT",
    "accept_executive_summary", "add_agenda_item", "approve_review", "complete_review",
    "create_review", "create_review_action", "delete_agenda_item", "delete_review_action",
    "discard_summary_draft", "draft_executive_summary", "ensure_iso_agenda", "generate_snapshot",
    "get_kpi_snapshot", "get_operational_kpi_summary", "start_review", "suggest_chair",
    "uncovered_mandatory_items", "update_agenda_item", "update_review", "update_review_action",
]

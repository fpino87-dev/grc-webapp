"""
Servizi del modulo controls, organizzati per area:

- evidence.py   — requisiti documentali/evidenze e copertura via extender (L2←L3)
- instances.py  — ciclo di vita ControlInstance: valutazione, applicabilità,
                  soft delete, propagazione cross-framework
- frameworks.py — governance framework: import/preview JSON, archive/delete
- gap.py        — gap analysis cross-framework via hub ISO (crosswalk C12)
- reporting.py  — compliance summary, conteggi per plant
- documents.py  — generazione documenti di procedura via AI

L'API pubblica resta `apps.controls.services.<funzione>` (re-export qui sotto).
"""

from .documents import generate_procedure_document
from .evidence import (
    calc_suggested_status,
    check_evidence_requirements,
    get_extender_instances,
    is_covered_by_extender,
)
from .frameworks import (
    archive_framework,
    delete_framework,
    import_framework_payload,
    list_framework_governance_metadata,
    preview_framework_import,
)
from .instances import (
    EVALUATED_STATUSES,
    apply_review_schedule,
    DOCUMENT_DEGRADED_TASK_PREFIX,
    can_delete_instance,
    degraded_only_by_documents,
    delete_control,
    delete_control_instance,
    evaluate_control,
    propagate_control,
    resolve_review_due_date,
    restore_controls_for_document,
    restore_document_degraded,
    set_implementation_description,
    validate_exclusion,
)
from .gap import run_gap_analysis
from .reporting import (
    count_open_gaps_by_plant,
    count_revaluation_by_plant,
    count_tisax_missing_implementation_by_plant,
    effective_control_rows,
    get_compliance_summary,
    summarize_compliance,
)

__all__ = [
    "DOCUMENT_DEGRADED_TASK_PREFIX",
    "EVALUATED_STATUSES",
    "apply_review_schedule",
    "archive_framework",
    "calc_suggested_status",
    "check_evidence_requirements",
    "count_open_gaps_by_plant",
    "count_revaluation_by_plant",
    "count_tisax_missing_implementation_by_plant",
    "can_delete_instance",
    "delete_control",
    "delete_control_instance",
    "delete_framework",
    "effective_control_rows",
    "degraded_only_by_documents",
    "evaluate_control",
    "restore_controls_for_document",
    "restore_document_degraded",
    "generate_procedure_document",
    "get_compliance_summary",
    "summarize_compliance",
    "get_extender_instances",
    "import_framework_payload",
    "is_covered_by_extender",
    "resolve_review_due_date",
    "set_implementation_description",
    "list_framework_governance_metadata",
    "preview_framework_import",
    "propagate_control",
    "run_gap_analysis",
    "validate_exclusion",
]

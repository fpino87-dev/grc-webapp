"""
Servizi del modulo controls, organizzati per area:

- evidence.py   — requisiti documentali/evidenze e copertura via extender (L2←L3)
- instances.py  — ciclo di vita ControlInstance: valutazione, applicabilità,
                  soft delete, propagazione cross-framework
- frameworks.py — governance framework: import/preview JSON, archive/delete
- reporting.py  — gap analysis, compliance summary, conteggi per plant
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
    delete_control_instance,
    evaluate_control,
    propagate_control,
    validate_exclusion,
)
from .reporting import (
    count_open_gaps_by_plant,
    count_revaluation_by_plant,
    gap_analysis,
    get_compliance_summary,
)

__all__ = [
    "archive_framework",
    "calc_suggested_status",
    "check_evidence_requirements",
    "count_open_gaps_by_plant",
    "count_revaluation_by_plant",
    "delete_control_instance",
    "delete_framework",
    "evaluate_control",
    "gap_analysis",
    "generate_procedure_document",
    "get_compliance_summary",
    "get_extender_instances",
    "import_framework_payload",
    "is_covered_by_extender",
    "list_framework_governance_metadata",
    "preview_framework_import",
    "propagate_control",
    "validate_exclusion",
]

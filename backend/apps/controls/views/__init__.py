"""
View del modulo controls, organizzate per area:

- frameworks.py    — catalogo: Framework, ControlDomain, Control (+ import/export AI)
- instances.py     — ControlInstance per plant: valutazione, link doc/evidenze, SOA
- reports.py       — gap analysis e export compliance (SOA, VDA ISA, matrice NIS2)
- audit_package.py — ZIP pronto-auditor con documenti ed evidenze

L'API pubblica resta `apps.controls.views.<Classe>` (re-export qui sotto);
`urls.py` è invariato.
"""

from .audit_package import AuditPackageView
from .frameworks import ControlDomainViewSet, ControlViewSet, FrameworkViewSet
from .instances import ControlInstanceViewSet
from .reports import ComplianceExportView, GapAnalysisView

__all__ = [
    "AuditPackageView",
    "ComplianceExportView",
    "ControlDomainViewSet",
    "ControlInstanceViewSet",
    "ControlViewSet",
    "FrameworkViewSet",
    "GapAnalysisView",
]

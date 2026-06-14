"""RBAC modulo Reporting (newfix F1)."""
from apps.auth_grc.models import GrcRole
from core.permissions import RoleScopedPermission


class ReportingPermission(RoleScopedPermission):
    """Dashboard di compliance/rischio in lettura per governance + audit.
    Le **scritture** sotto questo permesso non sono report ma configurazione
    ISMS (import di definizioni KPI, ricalcolo snapshot): riservate ai ruoli di
    governance — gli auditor (interni/esterni) sono osservatori e non
    configurano l'ISMS."""
    read_roles = {
        GrcRole.SUPER_ADMIN,
        GrcRole.COMPLIANCE_OFFICER,
        GrcRole.RISK_MANAGER,
        GrcRole.PLANT_MANAGER,
        GrcRole.INTERNAL_AUDITOR,
        GrcRole.EXTERNAL_AUDITOR,
    }
    write_roles = {
        GrcRole.SUPER_ADMIN,
        GrcRole.COMPLIANCE_OFFICER,
        GrcRole.RISK_MANAGER,
        GrcRole.PLANT_MANAGER,
    }


class AccessReviewPermission(RoleScopedPermission):
    """Matrice Accessi & Responsabilita': espone CHI ha accesso/responsabilita'
    su cosa (dati di tutti gli utenti) → ristretta a chi conduce la user-access
    review (ISO 27001 A.9.2.5): governance + audit. NON i ruoli operativi."""
    read_roles = {
        GrcRole.SUPER_ADMIN,
        GrcRole.COMPLIANCE_OFFICER,
        GrcRole.INTERNAL_AUDITOR,
        GrcRole.EXTERNAL_AUDITOR,
    }
    write_roles = read_roles

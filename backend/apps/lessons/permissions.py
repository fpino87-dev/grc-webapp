"""RBAC modulo Lessons Learned (newfix F1)."""
from apps.auth_grc.models import GrcRole
from core.permissions import RoleScopedPermission, org_wide_write_allowed


class LessonLearnedPermission(RoleScopedPermission):
    """Tutti i ruoli operativi possono leggere; scrittura per chi ha
    responsabilita' GRC operative (esclusi external_auditor read-only)."""
    read_roles = {
        GrcRole.SUPER_ADMIN,
        GrcRole.COMPLIANCE_OFFICER,
        GrcRole.RISK_MANAGER,
        GrcRole.PLANT_MANAGER,
        GrcRole.CONTROL_OWNER,
        GrcRole.INTERNAL_AUDITOR,
        GrcRole.EXTERNAL_AUDITOR,
    }
    write_roles = {
        GrcRole.SUPER_ADMIN,
        GrcRole.COMPLIANCE_OFFICER,
        GrcRole.RISK_MANAGER,
        GrcRole.PLANT_MANAGER,
        GrcRole.CONTROL_OWNER,
    }

    def has_object_permission(self, request, view, obj) -> bool:  # type: ignore[override]
        # Lesson di organizzazione (senza sito): scritture solo con scope org.
        return org_wide_write_allowed(request, obj.plant_id)


from typing import Optional

from django.contrib.auth import get_user_model
from django.db import models

from apps.plants.models import Plant
from .models import GrcRole, UserPlantAccess


def resolve_current_risk_manager(plant: Plant) -> Optional[get_user_model()]:
    """Risoluzione dinamica del ruolo su plant."""
    access = (
        UserPlantAccess.objects.filter(
            role=GrcRole.RISK_MANAGER,
            scope_type__in=["org", "single_plant", "plant_list"],
            deleted_at__isnull=True,
        )
        .select_related("user")
        .first()
    )
    return access.user if access else None


def competency_gap_analysis(user) -> dict:
    """
    Confronta le competenze richieste per i ruoli di governance attivi dell'utente
    (RoleAssignment M00) con le competenze effettive.
    """
    from .models import RoleCompetencyRequirement, UserCompetency
    from apps.governance.models import RoleAssignment
    from django.utils import timezone

    today = timezone.now().date()
    roles = list(
        RoleAssignment.objects.filter(
            user=user,
            deleted_at__isnull=True,
            valid_from__lte=today,
        ).filter(
            models.Q(valid_until__isnull=True) | models.Q(valid_until__gte=today)
        ).values_list("role", flat=True).distinct()
    )

    requirements = RoleCompetencyRequirement.objects.filter(
        grc_role__in=roles, mandatory=True
    )

    user_competencies = {
        uc.competency: uc
        for uc in UserCompetency.objects.filter(user=user)
    }

    gaps = []
    ok = []
    warnings = []

    for req in requirements:
        uc = user_competencies.get(req.competency)
        if uc is None:
            gaps.append({
                "competency":     req.competency,
                "role":           req.grc_role,
                "required_level": req.required_level,
                "current_level":  0,
                "gap":            req.required_level,
                "evidence_type":  req.evidence_type,
            })
        elif uc.level < req.required_level:
            gaps.append({
                "competency":     req.competency,
                "role":           req.grc_role,
                "required_level": req.required_level,
                "current_level":  uc.level,
                "gap":            req.required_level - uc.level,
                "evidence_type":  req.evidence_type,
            })
        elif not uc.is_valid:
            warnings.append({
                "competency": req.competency,
                "expired_on": str(uc.valid_until),
                "message":    f"Competenza scaduta il {uc.valid_until}",
            })
        else:
            ok.append(req.competency)

    return {
        "user_id":        str(user.pk),
        "user_name":      f"{user.first_name} {user.last_name}".strip() or user.email,
        "governance_roles": roles,
        "gaps":      gaps,
        "ok":        ok,
        "warnings":  warnings,
        "gap_count": len(gaps),
    }


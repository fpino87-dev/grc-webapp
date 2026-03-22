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


def anonymize_user(user, requesting_user) -> None:
    """
    Anonimizza i dati personali di un utente rimosso.
    GDPR Art. 17 — Diritto alla cancellazione.
    Preserva i record di audit trail (obbligo legale)
    ma rimuove i dati identificativi.
    """
    import uuid
    from django.utils import timezone
    from core.audit import log_action

    anon_id = str(uuid.uuid4())[:8]
    anon_email = f"deleted_{anon_id}@anonymized.invalid"

    # Anonimizza utente Django
    user.first_name = "Utente"
    user.last_name = "Rimosso"
    user.email = anon_email
    user.username = anon_email
    user.is_active = False
    user.set_unusable_password()
    user.save()

    # Soft delete accessi GRC
    UserPlantAccess.objects.filter(user=user).update(deleted_at=timezone.now())

    # Anonimizza nei log (preserva action_code e payload
    # ma rimuove l'email identificativa)
    from core.models import AuditLog
    AuditLog.objects.filter(
        user_email_at_time=user.email
    ).update(user_email_at_time=anon_email)

    log_action(
        user=requesting_user,
        action_code="auth.user.anonymized",
        level="L1",
        entity=user,
        payload={"anon_id": anon_id, "gdpr_request": True},
    )


def resolve_plant_member_emails(plant: Plant) -> list[str]:
    """
    Restituisce tutte le email degli utenti che hanno accesso al plant
    tramite UserPlantAccess (qualsiasi ruolo).
    """
    User = get_user_model()
    access_qs = (
        UserPlantAccess.objects.filter(
            deleted_at__isnull=True,
        )
        .select_related("user", "scope_bu")
        .prefetch_related("scope_plants")
    )

    emails: set[str] = set()
    for access in access_qs:
        user = access.user
        if not user or not user.is_active or not user.email:
            continue

        if access.scope_type == "org":
            emails.add(user.email)
        elif access.scope_type == "bu" and access.scope_bu and plant.bu_id == access.scope_bu_id:
            emails.add(user.email)
        elif access.scope_type in ("plant_list", "single_plant") and access.scope_plants.filter(pk=plant.pk).exists():
            emails.add(user.email)

    return list(emails)


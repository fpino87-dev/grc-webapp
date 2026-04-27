from typing import Optional

from django.contrib.auth import get_user_model
from django.db import models

from apps.plants.models import Plant
from .models import GrcRole, UserPlantAccess


def resolve_current_risk_manager(plant: Plant) -> Optional[get_user_model()]:
    """
    Risolve il Risk Manager competente per il plant dato, in ordine di priorità:
    1. Plant-specific (scope_type single_plant/plant_list con plant nello scope)
    2. Business Unit (scope_type bu con scope_bu == plant.bu)
    3. Org-wide (scope_type org)
    Restituisce None se nessun RM è assegnato al plant.
    """
    base_qs = UserPlantAccess.objects.filter(
        role=GrcRole.RISK_MANAGER,
        deleted_at__isnull=True,
    ).select_related("user").filter(user__is_active=True)

    plant_specific = base_qs.filter(
        scope_type__in=["single_plant", "plant_list"],
        scope_plants=plant,
    ).first()
    if plant_specific:
        return plant_specific.user

    if plant.bu_id:
        bu_match = base_qs.filter(scope_type="bu", scope_bu_id=plant.bu_id).first()
        if bu_match:
            return bu_match.user

    org_wide = base_qs.filter(scope_type="org").first()
    return org_wide.user if org_wide else None


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


def deactivate_grc_user(user, actor) -> None:
    """
    Disattiva un utente GRC (revoca accesso) senza anonimizzazione GDPR.
    Soft-delete degli UserPlantAccess attivi.
    """
    from django.core.exceptions import ValidationError
    from django.utils import timezone
    from django.utils.translation import gettext as _

    from core.audit import log_action

    if user.pk == actor.pk:
        raise ValidationError(_("Non puoi disattivare il tuo account da qui."))
    if user.is_superuser and not actor.is_superuser:
        raise ValidationError(_("Operazione non consentita su un account superuser."))

    user.is_active = False
    user.save(update_fields=["is_active"])

    UserPlantAccess.objects.filter(user=user, deleted_at__isnull=True).update(
        deleted_at=timezone.now()
    )

    log_action(
        user=actor,
        action_code="auth.user.deactivated",
        level="L2",
        entity=user,
        payload={"user_id": user.pk},
    )


def anonymize_user(user, requesting_user) -> None:
    """
    Anonimizza i dati personali di un utente rimosso.
    GDPR Art. 17 — Diritto alla cancellazione.

    L'audit trail è append-only (trigger PostgreSQL `audit_no_mutation`) e
    contiene già email pseudonimizzate via `_pseudonymize_email` al momento
    dell'evento (es. "mar***@***.com"): non è quindi necessario — né
    consentito senza bypassare il trigger — riscrivere i record storici.
    L'identità completa è ricavabile solo via `user_id`, che dopo
    l'anonimizzazione non è più mappato all'utente reale nel DB User.
    """
    import uuid
    from django.db import transaction
    from django.utils import timezone
    from core.audit import log_action

    anon_id = str(uuid.uuid4())[:8]
    anon_email = f"deleted_{anon_id}@anonymized.invalid"

    with transaction.atomic():
        user.first_name = "Utente"
        user.last_name = "Rimosso"
        user.email = anon_email
        user.username = anon_email
        user.is_active = False
        user.set_unusable_password()
        user.save()

        UserPlantAccess.objects.filter(user=user).update(deleted_at=timezone.now())

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


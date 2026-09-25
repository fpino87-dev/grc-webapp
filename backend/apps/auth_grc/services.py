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

    today = timezone.localdate()
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


def anonymize_user(user, requesting_user, *, reason: str = "") -> None:
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

    payload = {"anon_id": anon_id, "gdpr_request": True}
    # newfix F2 — la motivazione (richiesta GDPR Art. 17) e' richiesta dal
    # caller e va loggata per traceability dell'auditor.
    if reason:
        payload["reason"] = reason[:500]
    log_action(
        user=requesting_user,
        action_code="auth.user.anonymized",
        level="L1",
        entity=user,
        payload=payload,
    )


def resolve_plant_member_emails(plant: Plant) -> list[str]:
    """
    Restituisce tutte le email degli utenti che hanno accesso al plant
    tramite UserPlantAccess (qualsiasi ruolo).
    """
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


def _plant_access_filter(plant: Plant) -> models.Q:
    """Condizione UserPlantAccess che copre il plant dato, su tutti gli scope:
    org (tutti i plant), bu (stessa BU del plant), single_plant/plant_list
    (plant esplicitamente nello scope)."""
    cond = models.Q(scope_type="org")
    if plant.bu_id:
        cond |= models.Q(scope_type="bu", scope_bu_id=plant.bu_id)
    cond |= models.Q(scope_type__in=("single_plant", "plant_list"), scope_plants=plant)
    return cond


def user_has_plant_access(user, plant: Plant) -> bool:
    """True se l'utente ha accesso al plant via UserPlantAccess (qualsiasi ruolo)."""
    if user is None:
        return False
    return (
        UserPlantAccess.objects.filter(deleted_at__isnull=True, user=user)
        .filter(_plant_access_filter(plant))
        .exists()
    )


def eligible_owners_for_plant(plant: Plant) -> list[dict]:
    """Utenti assegnabili come owner di un controllo del plant: hanno accesso al
    plant via UserPlantAccess (qualsiasi ruolo). Restituisce [{id, name, role}],
    deduplicato per utente (un utente con più assegnazioni mantiene il primo
    ruolo per scope più specifico) e ordinato per nome."""
    access_qs = (
        UserPlantAccess.objects.filter(deleted_at__isnull=True, user__is_active=True)
        .filter(_plant_access_filter(plant))
        .select_related("user")
    )
    # scope più specifico prima (single/list > bu > org), così il ruolo mostrato
    # è quello che concede l'accesso più mirato al plant.
    scope_rank = {"single_plant": 0, "plant_list": 0, "bu": 1, "org": 2}
    by_user: dict[int, dict] = {}
    for access in access_qs:
        user = access.user
        if user.pk in by_user:
            if scope_rank.get(access.scope_type, 9) >= by_user[user.pk]["_rank"]:
                continue
        name = f"{user.first_name} {user.last_name}".strip() or user.email or user.username
        by_user[user.pk] = {
            "id": user.pk,
            "name": name,
            "role": access.role,
            "_rank": scope_rank.get(access.scope_type, 9),
        }
    result = [{"id": v["id"], "name": v["name"], "role": v["role"]} for v in by_user.values()]
    result.sort(key=lambda u: u["name"].lower())
    return result



# ── Catalogo ruoli: cosa può fare ogni ruolo ─────────────────────────────────

# Aree mostrate nella matrice "cosa può fare un ruolo", nell'ordine della UI:
# (chiave i18n dell'area, percorso della permission class). La matrice si
# legge dalle permission class reali (read_roles / write_roles), quindi non
# può divergere dal codice; il test di guardia verifica che ogni nuova
# RoleScopedPermission sia mappata qui o esclusa esplicitamente.
ROLE_MATRIX_AREAS = [
    ("governance", "apps.governance.permissions.GovernancePermission"),
    ("security_objectives", "apps.governance.permissions.SecurityObjectivePermission"),
    ("plants", "apps.plants.permissions.PlantPermission"),
    ("plant_config", "apps.plants.permissions.PlantConfigPermission"),
    ("frameworks", "apps.controls.permissions.FrameworkPermission"),
    ("controls", "apps.controls.permissions.ControlInstancePermission"),
    ("controls_assign", "apps.controls.permissions.ControlInstanceAssignPermission"),
    ("soa_approval", "apps.controls.permissions.SoAApprovalPermission"),
    ("vda_interview", "apps.controls.permissions.VdaInterviewPermission"),
    ("controls_reports", "apps.controls.permissions.ControlsReportPermission"),
    ("assets", "apps.assets.permissions.AssetPermission"),
    ("bia", "apps.bia.permissions.BiaPermission"),
    ("risk", "apps.risk.permissions.RiskPermission"),
    ("risk_appetite", "apps.risk.permissions.RiskAppetitePermission"),
    ("documents", "apps.documents.permissions.DocumentPermission"),
    ("tasks", "apps.tasks.permissions.TaskPermission"),
    ("checklist_delete", "apps.tasks.permissions.ChecklistRunDeletePermission"),
    ("kpi_config", "apps.tasks.permissions.KpiConfigPermission"),
    ("incidents", "apps.incidents.permissions.IncidentPermission"),
    ("nis2_config", "apps.incidents.permissions.NIS2ConfigurationPermission"),
    ("pdca", "apps.pdca.permissions.PdcaPermission"),
    ("lessons", "apps.lessons.permissions.LessonLearnedPermission"),
    ("management_review", "apps.management_review.permissions.ManagementReviewPermission"),
    ("suppliers", "apps.suppliers.permissions.SupplierPermission"),
    ("training", "apps.training.permissions.TrainingPermission"),
    ("training_records", "apps.training.permissions.TrainingRecordsPermission"),
    ("bcp", "apps.bcp.permissions.BcpPermission"),
    ("audit_prep", "apps.audit_prep.permissions.AuditPrepPermission"),
    ("reporting", "apps.reporting.permissions.ReportingPermission"),
    ("access_review", "apps.reporting.permissions.AccessReviewPermission"),
    ("schedule_policy", "apps.compliance_schedule.permissions.CompliancePolicyPermission"),
    ("ai_engine", "apps.ai_engine.permissions.AiEnginePermission"),
    ("competencies", "apps.auth_grc.permissions.CompetencyPermission"),
]
# Varianti che non aggiungono un'area distinta (stessi ruoli di un'altra).
ROLE_MATRIX_EXCLUDED = {
    "apps.management_review.permissions.ReviewWithBodyMembersPermission",
}


def role_permission_matrix() -> dict:
    """Per ogni area e ruolo: "W" modifica, "R" consultazione, "-" nessun
    accesso. Letta dalle permission class del codice. La gestione di utenti e
    accessi è riservata al super admin (IsGrcSuperAdmin)."""
    import importlib

    roles = [r.value for r in GrcRole]
    areas = []
    for key, path in ROLE_MATRIX_AREAS:
        module_path, cls_name = path.rsplit(".", 1)
        cls = getattr(importlib.import_module(module_path), cls_name, None)
        if cls is None:
            continue
        read = {str(r) for r in cls.read_roles}
        write = {str(r) for r in (cls.write_roles or cls.read_roles)}
        areas.append({
            "key": key,
            "perms": {r: "W" if r in write else "R" if r in read else "-" for r in roles},
        })
    areas.append({"key": "users", "perms": {r: "W" if r == GrcRole.SUPER_ADMIN else "-" for r in roles}})
    return {"roles": roles, "areas": areas}


# ── Coerenza responsabilità ↔ accessi ────────────────────────────────────────

def access_coverage(accesses, bu_plants: dict) -> tuple[bool, set]:
    """(ha scope org, id dei siti coperti) dagli accessi già caricati."""
    plants: set = set()
    for a in accesses:
        if a.scope_type == "org":
            return True, set()
        if a.scope_type == "bu" and a.scope_bu_id:
            plants |= bu_plants.get(a.scope_bu_id, set())
        else:
            plants |= {p.pk for p in a.scope_plants.all()}
    return False, plants


def responsibility_access_gaps(user, accesses, responsibilities, bu_plants: dict) -> list[dict]:
    """Responsabilità attive non coperte da un accesso al portale sullo stesso
    perimetro (es. DPO del sito TB senza accesso su TB): chi è responsabile
    deve poter vedere i dati di cui risponde."""
    if user.is_superuser:
        return []
    org, plants = access_coverage(accesses, bu_plants)
    if org:
        return []
    gaps = []
    for r in responsibilities:
        if r.scope_type == "org":
            covered = False
        elif r.scope_type == "bu":
            needed = bu_plants.get(r.scope_id, set())
            covered = bool(needed) and needed <= plants
        else:
            covered = r.scope_id in plants
        if not covered:
            gaps.append({"responsibility": str(r.pk), "role": r.role, "scope_type": r.scope_type,
                         "scope_id": str(r.scope_id) if r.scope_id else None})
    return gaps


def bu_plants_map() -> dict:
    """{bu_id: {plant_id, …}} dei siti attivi, per il calcolo delle coperture."""
    result: dict = {}
    for pid, bu_id in Plant.objects.filter(bu__isnull=False).values_list("pk", "bu_id"):
        result.setdefault(bu_id, set()).add(pid)
    return result


# ── Nuovo utente con i suoi accessi ──────────────────────────────────────────

def create_grc_user(*, actor, data: dict, password: str, accesses: list[dict]):
    """Crea l'utente e, nella stessa transazione, gli accessi scelti (ruolo +
    perimetro). Ogni accesso passa dalla stessa validazione del pannello
    accessi (perimetro per sito o BU mai vuoto)."""
    from django.db import transaction

    from core.audit import log_action
    from .serializers import UserPlantAccessSerializer

    User = get_user_model()
    with transaction.atomic():
        user = User(**data)
        user.set_password(password)
        user.save()
        log_action(user=actor, action_code="auth.user.created", level="L2", entity=user,
                   payload={"user_id": user.pk, "accesses": len(accesses)})
        for raw in accesses:
            ser = UserPlantAccessSerializer(data={**raw, "user": user.pk})
            ser.is_valid(raise_exception=True)
            access = ser.save(created_by=actor)
            log_action(
                user=actor, action_code="auth.access.granted", level="L2", entity=access,
                payload={"event": "granted", "access_id": str(access.pk), "user_id": str(user.pk),
                         "role": access.role, "scope_type": access.scope_type},
            )
    return user

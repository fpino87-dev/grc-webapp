from django.db.models import QuerySet

from .models import Plant


def _zoneinfo_or_default(tz_name: str):
    """
    ZoneInfo dal nome IANA, con fallback al TIME_ZONE di progetto se il valore
    è vuoto o non valido — un dato sporco non deve mai far esplodere un
    calcolo di scadenza.
    """
    import zoneinfo

    from django.conf import settings

    tz_name = (tz_name or "").strip() or settings.TIME_ZONE
    try:
        return zoneinfo.ZoneInfo(tz_name)
    except (zoneinfo.ZoneInfoNotFoundError, ValueError, KeyError):
        return zoneinfo.ZoneInfo(settings.TIME_ZONE)


def plant_timezone(plant):
    """ZoneInfo del sito (`Plant.timezone`, nome IANA), con fallback robusto."""
    return _zoneinfo_or_default(getattr(plant, "timezone", ""))


def plant_today(plant=None):
    """
    Data "oggi" nel fuso orario del sito. Con `plant=None` equivale a
    `timezone.localdate()` (orologio server / TIME_ZONE di progetto).

    Da usare nei calcoli scaduto/in-scadenza per-plant (scadenzario, advisor
    Cockpit, badge): la mezzanotte che conta è quella del sito, non quella
    del server. I job Celery schedulati restano sull'orologio del server.
    """
    from django.utils import timezone as dj_timezone

    if plant is None:
        return dj_timezone.localdate()
    return dj_timezone.localdate(timezone=plant_timezone(plant))


def plant_ids_by_today() -> dict:
    """
    Raggruppa i plant attivi per data "oggi" nel rispettivo fuso orario:
    `{date: [plant_id, ...]}` — un solo gruppo se tutti i siti condividono il
    fuso (caso comune).

    Pensata per gli advisor Cockpit: permette di mantenere una sola query
    aggregata per advisor costruendo una `Q` per gruppo (vedi
    `cockpit.advisors_builtin._per_plant_today_q`) invece di una query per plant.
    """
    from collections import defaultdict

    from django.utils import timezone as dj_timezone

    today_by_tz: dict[str, object] = {}
    groups: dict = defaultdict(list)
    for pid, tz_name in Plant.objects.filter(deleted_at__isnull=True).values_list("id", "timezone"):
        key = tz_name or ""
        if key not in today_by_tz:
            today_by_tz[key] = dj_timezone.localdate(timezone=_zoneinfo_or_default(key))
        groups[today_by_tz[key]].append(pid)
    return dict(groups)


def per_plant_today_q(build):
    """
    `Q` per confronti con l'"oggi" del sito (F3, timezone per Plant) senza
    rompere le query aggregate: i plant attivi vengono raggruppati per data
    odierna nel loro fuso (`plant_ids_by_today`, un solo gruppo se il fuso è
    unico) e `build(today, plant_ids)` produce la Q del gruppo; il risultato è
    l'OR dei gruppi — la query chiamante resta una sola.

    NB: righe con `plant_id` NULL non matchano nessun gruppo — se vanno
    incluse, aggiungere una clausola dedicata lato chiamante.
    """
    from django.db.models import Q

    cond = Q(pk__in=[])  # base che non matcha nulla (nessun plant attivo)
    for today, ids in plant_ids_by_today().items():
        cond |= build(today, ids)
    return cond


def get_active_frameworks(plant):
    """
    Restituisce i Framework attivi per un plant.
    Se plant è None restituisce tutti i framework non archiviati.
    """
    from apps.controls.models import Framework
    if plant is None:
        return Framework.objects.filter(archived_at__isnull=True)
    return Framework.objects.filter(
        plantframework__plant=plant,
        plantframework__active=True,
        archived_at__isnull=True,
    ).distinct()


def get_active_framework_codes(plant) -> list:
    """Restituisce lista di codici framework attivi per il plant."""
    return list(get_active_frameworks(plant).values_list("code", flat=True))


def get_nis2_plants() -> QuerySet[Plant]:
    return Plant.objects.filter(nis2_scope__in=["essenziale", "importante"], deleted_at__isnull=True)


def _cascade_delete_plant(plant: Plant, user) -> None:
    """Soft-delete in cascata di tutte le dipendenze del plant, poi del plant stesso."""
    from django.utils import timezone
    from apps.controls.models import ControlInstance
    from apps.assets.models import Asset
    from apps.bia.models import CriticalProcess
    from apps.risk.models import RiskAssessment
    from apps.documents.models import Document, Evidence
    from apps.tasks.models import Task
    from apps.incidents.models import Incident
    from apps.pdca.models import PdcaCycle
    from apps.lessons.models import LessonLearned
    from apps.management_review.models import ManagementReview
    from apps.bcp.models import BcpPlan
    from apps.audit_prep.models import AuditPrep, AuditProgram
    from apps.compliance_schedule.models import ComplianceSchedulePolicy
    from apps.governance.models import RoleAssignment
    from core.audit import log_action

    now = timezone.now()

    ControlInstance.objects.filter(plant=plant, deleted_at__isnull=True).update(deleted_at=now)
    Asset.objects.filter(plant=plant, deleted_at__isnull=True).update(deleted_at=now)
    CriticalProcess.objects.filter(plant=plant, deleted_at__isnull=True).update(deleted_at=now)
    RiskAssessment.objects.filter(plant=plant, deleted_at__isnull=True).update(deleted_at=now)
    Document.objects.filter(plant=plant, deleted_at__isnull=True).update(deleted_at=now)
    Evidence.objects.filter(plant=plant, deleted_at__isnull=True).update(deleted_at=now)
    Task.objects.filter(plant=plant, deleted_at__isnull=True).update(deleted_at=now)
    Incident.objects.filter(plant=plant, deleted_at__isnull=True).update(deleted_at=now)
    PdcaCycle.objects.filter(plant=plant, deleted_at__isnull=True).update(deleted_at=now)
    LessonLearned.objects.filter(plant=plant, deleted_at__isnull=True).update(deleted_at=now)
    ManagementReview.objects.filter(plant=plant, deleted_at__isnull=True).update(deleted_at=now)
    BcpPlan.objects.filter(plant=plant, deleted_at__isnull=True).update(deleted_at=now)
    AuditPrep.objects.filter(plant=plant, deleted_at__isnull=True).update(deleted_at=now)
    AuditProgram.objects.filter(plant=plant, deleted_at__isnull=True).update(deleted_at=now)
    ComplianceSchedulePolicy.objects.filter(plant=plant, deleted_at__isnull=True).update(deleted_at=now)
    RoleAssignment.objects.filter(scope_type="plant", scope_id=plant.pk, deleted_at__isnull=True).update(deleted_at=now)
    plant.frameworks.filter(deleted_at__isnull=True).update(deleted_at=now)
    plant.sub_plants.filter(deleted_at__isnull=True).update(deleted_at=now)

    log_action(
        user=user,
        action_code="plants.force_delete",
        level="L1",
        entity=plant,
        payload={"id": str(plant.id), "code": plant.code, "name": plant.name},
    )
    plant.soft_delete()


def delete_plant(plant: Plant, user, force: bool = False) -> None:
    """
    Soft delete di un Plant.

    Se force=False (default) blocca se esistono dipendenze attive.
    Se force=True (solo superuser) elimina in cascata tutte le dipendenze
    con soft delete, poi elimina il plant.
    """
    from django.core.exceptions import ValidationError

    if force and not getattr(user, "is_superuser", False):
        raise ValidationError("Solo il superuser può forzare l'eliminazione del sito.")

    if force:
        _cascade_delete_plant(plant, user)
        return

    dependency_counts: dict[str, int] = {}

    # Sub-plant attivi
    dependency_counts["sub_plants"] = plant.sub_plants.filter(deleted_at__isnull=True).count()

    # Configurazione framework / controlli
    from apps.controls.models import ControlInstance

    dependency_counts["plant_frameworks"] = plant.frameworks.filter(deleted_at__isnull=True).count()
    dependency_counts["control_instances"] = ControlInstance.objects.filter(
        plant=plant, deleted_at__isnull=True
    ).count()

    # Moduli principali (dati operativi)
    from apps.assets.models import Asset
    from apps.bia.models import CriticalProcess
    from apps.risk.models import RiskAssessment
    from apps.documents.models import Document, Evidence
    from apps.tasks.models import Task
    from apps.incidents.models import Incident
    from apps.pdca.models import PdcaCycle
    from apps.lessons.models import LessonLearned
    from apps.management_review.models import ManagementReview
    from apps.suppliers.models import Supplier
    from apps.training.models import TrainingCourse, PhishingSimulation
    from apps.bcp.models import BcpPlan
    from apps.audit_prep.models import AuditPrep, AuditProgram
    from apps.compliance_schedule.models import ComplianceSchedulePolicy
    from apps.governance.models import RoleAssignment

    dependency_counts["assets"] = Asset.objects.filter(plant=plant, deleted_at__isnull=True).count()
    dependency_counts["bia_processes"] = CriticalProcess.objects.filter(
        plant=plant, deleted_at__isnull=True
    ).count()
    dependency_counts["risk_assessments"] = RiskAssessment.objects.filter(
        plant=plant, deleted_at__isnull=True
    ).count()
    dependency_counts["documents"] = Document.objects.filter(
        plant=plant, deleted_at__isnull=True
    ).count()
    dependency_counts["evidences"] = Evidence.objects.filter(plant=plant, deleted_at__isnull=True).count()
    dependency_counts["tasks"] = Task.objects.filter(plant=plant, deleted_at__isnull=True).count()
    dependency_counts["incidents"] = Incident.objects.filter(plant=plant, deleted_at__isnull=True).count()
    dependency_counts["pdca_cycles"] = PdcaCycle.objects.filter(plant=plant, deleted_at__isnull=True).count()
    dependency_counts["lessons"] = LessonLearned.objects.filter(plant=plant, deleted_at__isnull=True).count()
    dependency_counts["management_reviews"] = ManagementReview.objects.filter(
        plant=plant, deleted_at__isnull=True
    ).count()
    dependency_counts["suppliers"] = Supplier.objects.filter(
        plants=plant, deleted_at__isnull=True
    ).distinct().count()
    dependency_counts["training_courses"] = TrainingCourse.objects.filter(
        plants=plant, deleted_at__isnull=True
    ).distinct().count()
    dependency_counts["phishing_simulations"] = PhishingSimulation.objects.filter(
        plant=plant, deleted_at__isnull=True
    ).count()
    dependency_counts["bcp_plans"] = BcpPlan.objects.filter(plant=plant, deleted_at__isnull=True).count()
    dependency_counts["audit_preps"] = AuditPrep.objects.filter(plant=plant, deleted_at__isnull=True).count()
    dependency_counts["audit_programs"] = AuditProgram.objects.filter(plant=plant, deleted_at__isnull=True).count()
    dependency_counts["schedule_policies"] = ComplianceSchedulePolicy.objects.filter(
        plant=plant, deleted_at__isnull=True
    ).count()
    dependency_counts["role_assignments"] = RoleAssignment.objects.filter(
        scope_type="plant", scope_id=plant.pk, deleted_at__isnull=True
    ).count()

    blocking = {k: v for k, v in dependency_counts.items() if v}
    if blocking:
        err = ValidationError(
            "Impossibile eliminare il sito: sono presenti dipendenze collegate.",
            code="blocking_dependencies",
            params={"blocking": blocking},
        )
        raise err

    plant.soft_delete()

    from core.audit import log_action

    log_action(
        user=user,
        action_code="plants.delete",
        level="L1",
        entity=plant,
        payload={"id": str(plant.id), "code": plant.code, "name": plant.name},
    )

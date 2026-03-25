from django.db.models import QuerySet

from .models import Plant


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


def delete_plant(plant: Plant, user) -> None:
    """
    Soft delete di un Plant.

    Per sicurezza, l'eliminazione è consentita solo se non esistono dipendenze attive
    (asset, controlli, documenti, incidenti, task, ecc.) collegate al sito.
    """
    from django.core.exceptions import ValidationError

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
        parts = [f"{k}={v}" for k, v in sorted(blocking.items())]
        raise ValidationError(
            "Impossibile eliminare il sito: sono presenti dipendenze collegate (" + ", ".join(parts) + ")."
        )

    plant.soft_delete()

    from core.audit import log_action

    log_action(
        user=user,
        action_code="plants.delete",
        level="L1",
        entity=plant,
        payload={"id": str(plant.id), "code": plant.code, "name": plant.name},
    )

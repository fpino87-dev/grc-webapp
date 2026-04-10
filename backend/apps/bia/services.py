from .models import CriticalProcess


def calc_business_impact(process):
    """Returns a composite impact score 1-5"""
    return round((process.danno_reputazionale + process.danno_normativo + process.danno_operativo) / 3)


def get_unvalidated_processes(plant_id):
    return CriticalProcess.objects.filter(plant_id=plant_id, status="bozza")


def approve_process(process, user):
    from django.utils import timezone

    process.status = "approvato"
    process.approved_by = user
    process.approved_at = timezone.now()
    process.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])


def validate_process(process, user):
    from django.utils import timezone

    process.status = "validato"
    process.validated_by = user
    process.validated_at = timezone.now()
    process.save(update_fields=["status", "validated_by", "validated_at", "updated_at"])


def get_process_risk_bcp_snapshot(process: CriticalProcess) -> dict:
    """
    Ritorna una vista integrata BIA + Risk + BCP per un processo critico.
    Non effettua side-effect né logging audit: è solo read-model per API/UI.
    """
    from apps.risk.models import RiskAssessment
    from apps.bcp.models import BcpPlan

    # BIA / BCP targets e impatti
    bia = {
        "mtpd_hours": process.mtpd_hours,
        "mbco_pct": process.mbco_pct,
        "rto_target_hours": process.rto_target_hours,
        "rpo_target_hours": process.rpo_target_hours,
        "downtime_cost_hour": process.downtime_cost_hour,
        "fatturato_esposto_anno": process.fatturato_esposto_anno,
        "danno_reputazionale": process.danno_reputazionale,
        "danno_normativo": process.danno_normativo,
        "danno_operativo": process.danno_operativo,
        "criticality": process.criticality,
        "status": process.status,
    }

    # Rischi collegati (via FK RiskAssessment.critical_process)
    risk_qs = RiskAssessment.objects.filter(
        critical_process=process,
        deleted_at__isnull=True,
    ).select_related("asset")

    risks = []
    for r in risk_qs:
        risks.append(
            {
                "id": str(r.pk),
                "name": r.name,
                "assessment_type": r.assessment_type,
                "asset_id": str(r.asset_id) if r.asset_id else None,
                "score": r.score,
                "inherent_score": r.inherent_score,
                "risk_level": r.risk_level,
                "inherent_risk_level": r.inherent_risk_level,
                "risk_reduction_pct": r.risk_reduction_pct,
                "status": r.status,
                "treatment": r.treatment,
                "risk_accepted_formally": r.risk_accepted_formally,
                "risk_acceptance_expiry": r.risk_acceptance_expiry,
            }
        )

    # BCP collegati (FK + M2M)
    direct_plans = BcpPlan.objects.filter(
        deleted_at__isnull=True,
        critical_process=process,
    )
    m2m_plans = BcpPlan.objects.filter(
        deleted_at__isnull=True,
        critical_processes=process,
    ).exclude(pk__in=direct_plans.values_list("pk", flat=True))

    plans_qs = direct_plans.union(m2m_plans).select_related("plant")

    bcp_plans = []
    for p in plans_qs:
        bcp_plans.append(
            {
                "id": str(p.pk),
                "title": p.title,
                "plant_id": str(p.plant_id),
                "status": p.status,
                "rto_hours": p.rto_hours,
                "rpo_hours": p.rpo_hours,
                "last_test_date": p.last_test_date,
                "next_test_date": p.next_test_date,
            }
        )

    has_bcp_plan = len(bcp_plans) > 0
    has_high_risks_without_plan = any(
        r.get("risk_level") == "rosso" for r in risks
    ) and not has_bcp_plan

    summary = {
        "rto_bcp_status": process.rto_bcp_status,
        "has_bcp_plan": has_bcp_plan,
        "has_high_risks_without_plan": has_high_risks_without_plan,
    }

    return {
        "process_id": str(process.pk),
        "bia": bia,
        "risks": risks,
        "bcp_plans": bcp_plans,
        "summary": summary,
    }


def delete_process(process: CriticalProcess, user, cascade: bool = False) -> None:
    """
    Elimina (soft delete) un processo BIA.

    - cascade=false: elimina solo se non ci sono dipendenze attive.
    - cascade=true: elimina anche dipendenze correlate (RiskAssessment, BCP, ecc.) per pulizia di prova.
    """
    from django.core.exceptions import ValidationError
    from django.db.models import Q
    from core.audit import log_action

    from apps.risk.models import RiskAssessment
    from apps.bcp.models import BcpPlan
    from apps.assets.models import Asset

    from .models import RiskDecision, TreatmentOption

    if not cascade:
        has_risks = RiskAssessment.objects.filter(critical_process=process, deleted_at__isnull=True).exists()
        has_bcp_fk = process.bcp_plans.filter(deleted_at__isnull=True).exists()
        has_bcp_m2m = BcpPlan.objects.filter(deleted_at__isnull=True, critical_processes=process).exists()
        has_treatments = process.treatment_options.filter(deleted_at__isnull=True).exists()
        has_decisions = process.risk_decisions.filter(deleted_at__isnull=True).exists()
        has_assets = Asset.objects.filter(deleted_at__isnull=True, processes=process).exists()

        if any([has_risks, has_bcp_fk, has_bcp_m2m, has_treatments, has_decisions, has_assets]):
            raise ValidationError(
                "Impossibile eliminare il processo: esistono valutazioni rischio, BCP, opzioni di trattamento, decisioni o asset collegati."
            )

        process.soft_delete()
        log_action(
            user=user,
            action_code="bia.critical_process.deleted",
            level="L2",
            entity=process,
            payload={"id": str(process.id), "name": process.name},
        )
        return

    # Cascade: delete dependencies first.
    risk_assessments = (
        RiskAssessment.objects.filter(critical_process=process, deleted_at__isnull=True)
        .prefetch_related("dimensions", "mitigation_plans")
    )
    for assessment in risk_assessments:
        for dim in assessment.dimensions.all():
            dim.soft_delete()
            log_action(
                user=user,
                action_code="risk.dimension.deleted",
                level="L2",
                entity=dim,
                payload={"id": str(dim.id), "dimension_code": dim.dimension_code},
            )
        for mp in assessment.mitigation_plans.all():
            mp.soft_delete()
            log_action(
                user=user,
                action_code="risk.mitigation_plan.deleted",
                level="L2",
                entity=mp,
                payload={"id": str(mp.id), "due_date": str(mp.due_date)},
            )
        assessment.soft_delete()
        log_action(
            user=user,
            action_code="risk.assessment.deleted",
            level="L2",
            entity=assessment,
            payload={"id": str(assessment.id), "name": assessment.name},
        )

    for decision in process.risk_decisions.all():
        decision.soft_delete()
        log_action(
            user=user,
            action_code="bia.risk_decision.deleted",
            level="L2",
            entity=decision,
            payload={"id": str(decision.id)},
        )

    for option in process.treatment_options.all():
        option.soft_delete()
        log_action(
            user=user,
            action_code="bia.treatment_option.deleted",
            level="L2",
            entity=option,
            payload={"id": str(option.id), "title": option.title},
        )

    bcp_plans = (
        BcpPlan.objects.filter(deleted_at__isnull=True)
        .filter(Q(critical_process=process) | Q(critical_processes=process))
        .distinct()
        .prefetch_related("tests")
    )
    for plan in bcp_plans:
        for test in plan.tests.all():
            test.soft_delete()
            log_action(
                user=user,
                action_code="bcp.test.deleted",
                level="L2",
                entity=test,
                payload={"id": str(test.id), "result": test.result},
            )
        plan.soft_delete()
        log_action(
            user=user,
            action_code="bcp.plan.deleted",
            level="L2",
            entity=plan,
            payload={"id": str(plan.id), "title": plan.title},
        )

    process.soft_delete()
    log_action(
        user=user,
        action_code="bia.critical_process.deleted",
        level="L2",
        entity=process,
        payload={"id": str(process.id), "name": process.name, "cascade": True},
    )

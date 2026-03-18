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

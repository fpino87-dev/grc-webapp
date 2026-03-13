from decimal import Decimal

from django.utils import timezone

from .models import IMPACT_MAP, PROB_MAP, RiskAssessment


IT_WEIGHTS = {
    "esposizione": 0.30,
    "cve": 0.25,
    "minaccia": 0.25,
    "gap_controlli": 0.20,
}
OT_WEIGHTS = {
    "purdue_connettivita": 0.25,
    "patchability": 0.20,
    "impatto_fisico": 0.25,
    "segmentazione": 0.15,
    "rilevabilita": 0.15,
}


def calc_score(assessment: RiskAssessment) -> int:
    dims = {d.dimension_code: d.value for d in assessment.dimensions.all()}
    weights = IT_WEIGHTS if assessment.assessment_type == "IT" else OT_WEIGHTS
    weighted = sum(dims.get(k, 3) * w for k, w in weights.items())
    prob = min(5, round(weighted))
    impact = min(5, round(weighted))
    return min(25, prob * impact)


def calc_ale(assessment: RiskAssessment, process_ale: Decimal) -> Decimal:
    if assessment.score is None:
        return Decimal("0")
    prob_idx = max(1, min(5, round(assessment.score ** 0.5)))
    imp_idx = prob_idx
    return (
        Decimal(str(PROB_MAP[prob_idx]))
        * Decimal(str(IMPACT_MAP[imp_idx]))
        * process_ale
    )


def escalate_red_risk(assessment: RiskAssessment, user):
    from apps.tasks.services import create_task

    if assessment.risk_level != "rosso":
        return
    create_task(
        plant=assessment.plant,
        title=f"Piano mitigazione rischio critico — {assessment.asset}",
        priority="critica",
        source_module="M06",
        source_id=assessment.pk,
        due_date=timezone.now().date() + timezone.timedelta(days=15),
        assign_type="role",
        assign_value="risk_manager",
    )


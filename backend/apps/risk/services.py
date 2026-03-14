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


def calc_ale(assessment: RiskAssessment) -> Decimal:
    """
    Calcola ALE annuo partendo dai dati BIA del processo critico collegato.
    Formula: downtime_cost_hour × ore_fermo_stimato × probabilità_annua
    Se non c'è processo BIA collegato restituisce Decimal("0").
    """
    if not assessment.critical_process:
        return Decimal("0")
    cp = assessment.critical_process
    if not cp.downtime_cost_hour:
        return Decimal("0")
    ore_fermo_map = {1: 1, 2: 4, 3: 24, 4: 72, 5: 168}
    prob_annua_map = {1: 0.1, 2: 0.3, 3: 1.0, 4: 3.0, 5: 10.0}
    impact = assessment.impact or 3
    prob = assessment.probability or 3
    ore = ore_fermo_map.get(impact, 24)
    prob_a = prob_annua_map.get(prob, 1.0)
    ale = Decimal(str(cp.downtime_cost_hour)) * Decimal(str(ore)) * Decimal(str(prob_a))
    extra = Decimal("1.0")
    if cp.danno_reputazionale >= 4:
        extra += Decimal("0.3")
    if cp.danno_normativo >= 4:
        extra += Decimal("0.2")
    return (ale * extra).quantize(Decimal("0.01"))


def calc_score_from_dimensions(assessment: RiskAssessment) -> int:
    """Score pesato con RiskDimension IT/OT — usato quando disponibili."""
    dims = {d.dimension_code: d.value for d in assessment.dimensions.all()}
    if not dims:
        p = assessment.probability or 1
        i = assessment.impact or 1
        return min(25, p * i)
    weights = IT_WEIGHTS if assessment.assessment_type == "IT" else OT_WEIGHTS
    weighted = sum(dims.get(k, 3) * w for k, w in weights.items())
    prob = min(5, round(weighted))
    impact = min(5, round(weighted))
    return min(25, prob * impact)


def suggest_residual_score(assessment) -> dict:
    """
    Suggerisce il rischio residuo in base ai controlli compliant collegati al sito.
    Logica: parte dal rischio inerente, applica riduzione per controllo compliant (-2%, max 60%).
    """
    if not assessment.inherent_score:
        return {"suggested": None, "reason": "Rischio inerente non definito"}

    if not assessment.critical_process:
        return {
            "suggested": assessment.inherent_score,
            "reason": "Nessun processo BIA collegato — nessuna riduzione applicata",
        }

    from apps.controls.models import ControlInstance
    plant_controls = ControlInstance.objects.filter(
        plant=assessment.plant,
        status="compliant",
        deleted_at__isnull=True,
    )
    compliant_count = plant_controls.count()
    reduction_pct = min(60, compliant_count * 2)
    suggested = max(1, round(assessment.inherent_score * (1 - reduction_pct / 100)))

    return {
        "suggested": suggested,
        "reduction_pct": reduction_pct,
        "compliant_controls": compliant_count,
        "reason": (
            f"{compliant_count} controlli compliant → "
            f"riduzione stimata {reduction_pct}% → "
            f"score residuo suggerito: {suggested}"
        ),
    }


def accept_risk(assessment, user, note: str, expiry_date=None) -> None:
    """Accettazione formale del rischio residuo. Richiede nota obbligatoria."""
    from django.core.exceptions import ValidationError
    from django.utils import timezone
    from core.audit import log_action

    risk_lv = assessment.risk_level
    if risk_lv != "rosso" and not note:
        raise ValidationError("La nota è obbligatoria per l'accettazione formale del rischio.")
    if risk_lv == "rosso" and len(note.strip()) < 50:
        raise ValidationError(
            "Per rischi critici (rosso) la nota di accettazione deve essere di almeno 50 caratteri."
        )

    assessment.risk_accepted_formally = True
    assessment.risk_accepted_by = user
    assessment.risk_accepted_at = timezone.now()
    assessment.risk_acceptance_note = note
    assessment.risk_acceptance_expiry = expiry_date
    assessment.save(update_fields=[
        "risk_accepted_formally", "risk_accepted_by",
        "risk_accepted_at", "risk_acceptance_note",
        "risk_acceptance_expiry", "updated_at",
    ])

    log_action(
        user=user,
        action_code="risk.accepted_formally",
        level="L1",
        entity=assessment,
        payload={
            "score": assessment.score,
            "level": risk_lv,
            "note": note[:100],
            "expiry": str(expiry_date) if expiry_date else None,
        },
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


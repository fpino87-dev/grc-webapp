from django.utils import timezone
from core.audit import log_action
from .models import ManagementReview


def get_kpi_snapshot(plant_id) -> dict:
    """Return a dict with key metrics for the given plant."""
    from django.db.models import Count, Q
    from apps.controls.models import ControlInstance
    from apps.incidents.models import Incident
    from apps.risk.models import RiskAssessment

    controls_qs = ControlInstance.objects.filter(plant_id=plant_id)
    total_controls = controls_qs.count()
    compliant = controls_qs.filter(status="compliant").count()

    incidents_qs = Incident.objects.filter(plant_id=plant_id)
    open_incidents = incidents_qs.filter(status__in=["aperto", "in_analisi"]).count()

    risks_qs = RiskAssessment.objects.filter(plant_id=plant_id, status="completato")
    high_risks = risks_qs.filter(score__gt=14).count()

    return {
        "plant_id": str(plant_id),
        "controls_total": total_controls,
        "controls_compliant": compliant,
        "pct_compliant": round(compliant / total_controls * 100, 1) if total_controls else 0,
        "incidents_open": open_incidents,
        "risks_high": high_risks,
        "snapshot_at": timezone.now().isoformat(),
    }


def complete_review(review: ManagementReview, user) -> ManagementReview:
    """Transition a review to completato and snapshot KPIs."""
    if review.plant_id:
        review.kpi_snapshot = get_kpi_snapshot(review.plant_id)
    review.status = "completato"
    review.save(update_fields=["status", "kpi_snapshot", "updated_at"])
    log_action(
        user=user,
        action_code="management_review.review.complete",
        level="L2",
        entity=review,
        payload={"id": str(review.id), "title": review.title},
    )
    return review

from celery import shared_task
from django.utils import timezone
from django.db.models import Avg, Count, Q


@shared_task(name="apps.reporting.tasks.generate_weekly_kpi_snapshots")
def generate_weekly_kpi_snapshots():
    """
    Generate weekly ISMS KPI snapshots for every active plant × framework combination.
    Runs every Monday at 06:00 via Celery beat.
    Creates or updates IsmsKpiSnapshot for the current ISO week start.
    """
    from apps.plants.models import Plant
    from apps.controls.models import ControlInstance
    from .models import IsmsKpiSnapshot

    today = timezone.now().date()
    # Monday of current week
    week_start = today - timezone.timedelta(days=today.weekday())

    plants = list(Plant.objects.filter(status="attivo", deleted_at__isnull=True))
    # Collect distinct framework codes across all ControlInstances
    frameworks = list(
        ControlInstance.objects.filter(deleted_at__isnull=True)
        .values_list("control__framework__code", flat=True)
        .distinct()
    )

    created_count = 0
    updated_count = 0

    for plant in plants:
        for framework_code in frameworks:
            snapshot, is_new = _build_snapshot(plant, framework_code, week_start)
            if is_new:
                created_count += 1
            else:
                updated_count += 1

    # Also build org-wide snapshot (plant=None) for each framework
    for framework_code in frameworks:
        snapshot, is_new = _build_snapshot(None, framework_code, week_start)
        if is_new:
            created_count += 1
        else:
            updated_count += 1

    return {
        "week_start": str(week_start),
        "created": created_count,
        "updated": updated_count,
        "plants": len(plants),
        "frameworks": len(frameworks),
    }


def _build_snapshot(plant, framework_code: str, week_start):
    from apps.controls.models import ControlInstance
    from apps.risk.models import RiskAssessment
    from apps.incidents.models import Incident
    from .models import IsmsKpiSnapshot

    ci_qs = ControlInstance.objects.filter(
        deleted_at__isnull=True,
        control__framework__code=framework_code,
    )
    if plant is not None:
        ci_qs = ci_qs.filter(plant=plant)

    controls_total = ci_qs.count()
    controls_compliant = ci_qs.filter(status="compliant").count()
    controls_gap = ci_qs.filter(status="gap").count()
    pct_compliant = round(controls_compliant / controls_total * 100, 1) if controls_total else 0.0
    overall_maturity = _calc_overall_maturity(ci_qs)

    risk_qs = RiskAssessment.objects.filter(status="completato", deleted_at__isnull=True)
    if plant is not None:
        risk_qs = risk_qs.filter(plant=plant)
    open_risks = risk_qs.count()
    high_risks = risk_qs.filter(score__gt=14).count()

    inc_qs = Incident.objects.filter(deleted_at__isnull=True)
    if plant is not None:
        inc_qs = inc_qs.filter(plant=plant)
    open_incidents = inc_qs.filter(status__in=["aperto", "in_analisi"]).count()
    critical_incidents = inc_qs.filter(status__in=["aperto", "in_analisi"], severity="critico").count()

    defaults = dict(
        controls_total=controls_total,
        controls_compliant=controls_compliant,
        controls_gap=controls_gap,
        pct_compliant=pct_compliant,
        overall_maturity=overall_maturity,
        open_risks=open_risks,
        high_risks=high_risks,
        open_incidents=open_incidents,
        critical_incidents=critical_incidents,
    )

    obj, created = IsmsKpiSnapshot.objects.update_or_create(
        plant=plant,
        framework_code=framework_code,
        week_start=week_start,
        defaults=defaults,
    )
    return obj, created


def _calc_overall_maturity(ci_qs):
    """Return average maturity_level across ControlInstances, or None if no data."""
    result = ci_qs.filter(maturity_level__isnull=False).aggregate(avg=Avg("maturity_level"))
    return result["avg"]

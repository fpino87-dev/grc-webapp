from celery import shared_task
from django.utils import timezone
from django.db.models import Avg

# Vedi IsmsKpiSnapshot.method_version.
COMPLIANCE_METHOD_VERSION = 2


@shared_task(name="apps.reporting.tasks.generate_weekly_kpi_snapshots")
def generate_weekly_kpi_snapshots():
    """
    Generate weekly ISMS KPI snapshots for every active plant × framework combination.
    Runs every Monday at 06:00 via Celery beat.
    Creates or updates IsmsKpiSnapshot for the current ISO week start.
    """
    from apps.plants.models import Plant
    from apps.plants.services import get_active_framework_codes

    today = timezone.localdate()
    # Monday of current week
    week_start = today - timezone.timedelta(days=today.weekday())

    plants = list(Plant.objects.filter(status="attivo", deleted_at__isnull=True))
    # Per ogni sito solo i framework attivi su quel sito: un framework presente
    # altrove (o disattivato qui) non deve produrre una serie per questo sito.
    active_by_plant = {plant.pk: get_active_framework_codes(plant) for plant in plants}

    created_count = 0
    updated_count = 0

    for plant in plants:
        for framework_code in active_by_plant[plant.pk]:
            snapshot, is_new = _build_snapshot(plant, framework_code, week_start)
            if is_new:
                created_count += 1
            else:
                updated_count += 1

    # Snapshot di organizzazione (plant=None): per ogni framework attivo su
    # almeno un sito, sui soli siti che lo hanno attivo.
    plants_by_framework: dict[str, list] = {}
    for plant in plants:
        for framework_code in active_by_plant[plant.pk]:
            plants_by_framework.setdefault(framework_code, []).append(plant.pk)
    frameworks = sorted(plants_by_framework)
    for framework_code in frameworks:
        snapshot, is_new = _build_snapshot(
            None, framework_code, week_start, plant_ids=plants_by_framework[framework_code],
        )
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


def _build_snapshot(plant, framework_code: str, week_start, plant_ids=None):
    from apps.controls.models import ControlInstance
    from apps.risk.models import RiskAssessment
    from apps.incidents.models import Incident
    from .models import IsmsKpiSnapshot

    from apps.controls.services import effective_control_rows, summarize_compliance

    scope_ids = [plant.pk] if plant is not None else list(plant_ids or [])
    # Stessa regola del valore in tempo reale (Reporting, Assistente): N/A
    # esclusi e controlli base sostituiti da un extender attivo fuori conteggio.
    summary = summarize_compliance(effective_control_rows(scope_ids, [framework_code]))
    controls_total = summary["total"]
    controls_compliant = summary["compliant"]
    controls_gap = summary["gap"]
    pct_compliant = float(summary["pct_compliant"])

    ci_qs = ControlInstance.objects.filter(
        deleted_at__isnull=True,
        control__framework__code=framework_code,
        plant_id__in=scope_ids,
    )
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
    critical_incidents = inc_qs.filter(status__in=["aperto", "in_analisi"], severity="critica").count()

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
        method_version=COMPLIANCE_METHOD_VERSION,
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

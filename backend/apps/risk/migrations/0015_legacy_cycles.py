"""Archivia il registro esistente come valutazione con metodo superato.

Per ogni sito con rischi crea un RiskAssessmentCycle `legacy` / `archiviato`,
vi collega tutti i rischi e ne copia i valori del metodo precedente in
`legacy_snapshot`, così restano consultabili anche quando i campi spariranno
dal model. Nessun dato viene modificato o eliminato.
"""
from django.db import migrations
from django.utils import timezone

LEGACY_FIELDS = (
    "name", "assessment_type", "threat_category", "probability", "impact", "score",
    "inherent_probability", "inherent_impact", "inherent_score", "treatment", "status",
    "ale_annuo", "cause", "consequence", "risk_accepted", "risk_accepted_formally",
    "risk_acceptance_note", "risk_acceptance_expiry", "risk_accepted_at",
    "plan_due_date", "nis2_art21_category", "nis2_relevance", "impacted_systems",
    "needs_revaluation", "assessed_at",
)


def _json(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def forwards(apps, schema_editor):
    RiskAssessment = apps.get_model("risk", "RiskAssessment")
    RiskAssessmentCycle = apps.get_model("risk", "RiskAssessmentCycle")
    RiskDimension = apps.get_model("risk", "RiskDimension")

    now = timezone.now()
    # order_by() vuoto: l'ordinamento di default del model entrerebbe nella
    # DISTINCT e restituirebbe un "sito" per ogni rischio (un ciclo per rischio).
    plant_ids = set(
        RiskAssessment.objects.filter(cycle__isnull=True)
        .order_by().values_list("plant_id", flat=True).distinct()
    )
    for plant_id in plant_ids:
        risks = RiskAssessment.objects.filter(plant_id=plant_id, cycle__isnull=True)
        if not risks.exists():
            continue
        first = risks.order_by("created_at").values_list("created_at", flat=True).first()
        cycle = RiskAssessmentCycle.objects.create(
            plant_id=plant_id,
            kind="legacy",
            status="archiviato",
            started_at=first or now,
            closed_at=now,
        )
        for risk in risks:
            snapshot = {f: _json(getattr(risk, f)) for f in LEGACY_FIELDS}
            snapshot["owner_id"] = risk.owner_id
            snapshot["risk_accepted_by_id"] = risk.risk_accepted_by_id
            snapshot["dimensions"] = {
                d.dimension_code: d.value
                for d in RiskDimension.objects.filter(assessment_id=risk.pk)
            }
            risk.legacy_snapshot = snapshot
            risk.cycle_id = cycle.pk
            risk.save(update_fields=["legacy_snapshot", "cycle"])


class Migration(migrations.Migration):
    dependencies = [("risk", "0014_methodology_foundations")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]

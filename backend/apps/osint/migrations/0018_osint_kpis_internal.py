from django.db import migrations


def to_internal(apps, schema_editor):
    """Il KPI dei critici aperti passa dal push via API del lunedì al
    connettore interno del KPI engine (stesso codice: lo storico degli
    snapshot resta). Il job di push non serve più."""
    KPIDefinition = apps.get_model("tasks", "KPIDefinition")
    KPIDefinition.objects.filter(kpi_code="osint_critical_open_count", source="api").update(source="internal")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(task="osint.push_kpis").delete()

    # I KPI OSINT erano automatici (il push creava la definizione): restano
    # tali. Si creano le definizioni globali dei KPI nuovi, se mancano;
    # soglie e attivazione restano modificabili dall'utente.
    defaults = [
        ("osint_security_score", "Postura esterna",
         "Sicurezza esterna media (0–100, più alto = meglio) dei domini e degli asset esposti del sito.",
         "/100", "success_rate", "above", 75.0, 60.0),
        ("osint_critical_suppliers_at_risk_rate", "Fornitori critici a rischio (OSINT)",
         "Percentuale dei fornitori critici del sito con voto di postura esterna D o F.",
         "%", "success_rate", "below", 10.0, 25.0),
    ]
    for code, name, desc, unit, agg, direction, warn, crit in defaults:
        if not KPIDefinition.objects.filter(kpi_code=code, deleted_at__isnull=True).exists():
            KPIDefinition.objects.create(
                kpi_code=code, name=name, description=desc, unit=unit, source="internal",
                aggregation=agg, threshold_direction=direction, threshold_warning=warn,
                threshold_critical=crit, notify_on_warning=False, notify_on_critical=True, is_active=True,
            )


class Migration(migrations.Migration):

    dependencies = [
        ("osint", "0017_supply_chain_monitoring"),
        ("tasks", "0016_training_kpis_evidence_based"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [migrations.RunPython(to_internal, migrations.RunPython.noop)]

from django.db import migrations


def prune(apps, schema_editor):
    """Una tantum: allinea gli snapshot KPI già presenti allo scope corrente
    delle definizioni (stessa regola del task settimanale, apps.tasks.kpi_scope),
    senza aspettare il calcolo del lunedì. Soft delete, non DELETE."""
    from apps.tasks.kpi_scope import sync_snapshots_with_scope

    sync_snapshots_with_scope(
        KPIDefinition=apps.get_model("tasks", "KPIDefinition"),
        OperationalKpiSnapshot=apps.get_model("tasks", "OperationalKpiSnapshot"),
        Plant=apps.get_model("plants", "Plant"),
    )


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0016_training_kpis_evidence_based"),
        ("plants", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(prune, migrations.RunPython.noop),
    ]

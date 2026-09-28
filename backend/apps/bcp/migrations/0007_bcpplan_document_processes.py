from django.db import migrations, models
import django.db.models.deletion


def fk_to_m2m(apps, schema_editor):
    """Il processo del FK storico entra nell'elenco dei processi coperti."""
    BcpPlan = apps.get_model("bcp", "BcpPlan")
    for plan in BcpPlan.objects.filter(critical_process__isnull=False):
        plan.critical_processes.add(plan.critical_process_id)
        plan.critical_process_id = None
        plan.save(update_fields=["critical_process"])


class Migration(migrations.Migration):

    dependencies = [
        ("bcp", "0006_alter_bcptest_options"),
        ("documents", "0009_documentapproval_version"),
    ]

    operations = [
        migrations.AddField(
            model_name="bcpplan",
            name="document",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="bcp_plans", to="documents.document",
            ),
        ),
        migrations.RunPython(fk_to_m2m, migrations.RunPython.noop),
    ]

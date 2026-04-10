from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("incidents", "0004_alter_nis2configuration_deleted_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="incident",
            name="acn_is_category",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Nessuna"),
                    ("IS-1", "IS-1 (Perdita riservatezza verso esterno)"),
                    ("IS-2", "IS-2 (Perdita integrita con impatto esterno)"),
                    ("IS-3", "IS-3 (Violazione livelli di servizio/SLA)"),
                    ("IS-4", "IS-4 (Accesso non autorizzato/abuso privilegi)"),
                ],
                default="",
                help_text="Classificazione ACN IS-1/IS-2/IS-3/IS-4",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="incident",
            name="axis_confidentiality",
            field=models.PositiveSmallIntegerField(blank=True, help_text="Asse 4 (1-5)", null=True),
        ),
        migrations.AddField(
            model_name="incident",
            name="axis_economic",
            field=models.PositiveSmallIntegerField(blank=True, help_text="Asse 2 (1-5)", null=True),
        ),
        migrations.AddField(
            model_name="incident",
            name="axis_operational",
            field=models.PositiveSmallIntegerField(blank=True, help_text="Asse 1 (1-5)", null=True),
        ),
        migrations.AddField(
            model_name="incident",
            name="axis_people",
            field=models.PositiveSmallIntegerField(blank=True, help_text="Asse 3 (1-5)", null=True),
        ),
        migrations.AddField(
            model_name="incident",
            name="axis_recurrence",
            field=models.PositiveSmallIntegerField(default=0, help_text="Asse 6 (0 oppure 2)"),
        ),
        migrations.AddField(
            model_name="incident",
            name="axis_reputational",
            field=models.PositiveSmallIntegerField(blank=True, help_text="Asse 5 (1-5)", null=True),
        ),
        migrations.AddField(
            model_name="incident",
            name="is_recurrent",
            field=models.BooleanField(default=False, help_text="Evento ricorrente negli ultimi 6 mesi"),
        ),
        migrations.AddField(
            model_name="incident",
            name="pta_nis2",
            field=models.PositiveSmallIntegerField(
                blank=True, help_text="PTA NIS2 = max assi 1..5", null=True
            ),
        ),
        migrations.AddField(
            model_name="incident",
            name="ptnr_nis2",
            field=models.PositiveSmallIntegerField(
                blank=True, help_text="PTNR NIS2 = PTA + Asse ricorrenza", null=True
            ),
        ),
        migrations.AddField(
            model_name="incident",
            name="pt_gdpr",
            field=models.PositiveSmallIntegerField(
                blank=True, help_text="PT GDPR = Asse 4 * presenza dati personali (0/1)", null=True
            ),
        ),
        migrations.AddField(
            model_name="incident",
            name="requires_csirt_notification",
            field=models.BooleanField(help_text="True se incidente con obbligo notifica CSIRT", null=True),
        ),
        migrations.AddField(
            model_name="incident",
            name="requires_gdpr_notification",
            field=models.BooleanField(
                help_text="True se probabile obbligo notifica Garante Privacy", null=True
            ),
        ),
    ]

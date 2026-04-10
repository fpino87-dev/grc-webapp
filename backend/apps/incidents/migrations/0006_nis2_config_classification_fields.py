from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("incidents", "0005_incident_scoring_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="nis2configuration",
            name="multiplier_medium",
            field=models.DecimalField(
                decimal_places=2,
                default=2.0,
                help_text="Moltiplicatore soglia per punteggio 4 (default ×2)",
                max_digits=4,
            ),
        ),
        migrations.AddField(
            model_name="nis2configuration",
            name="multiplier_high",
            field=models.DecimalField(
                decimal_places=2,
                default=3.0,
                help_text="Moltiplicatore soglia per punteggio 5 (default ×3)",
                max_digits=4,
            ),
        ),
        migrations.AddField(
            model_name="nis2configuration",
            name="recurrence_window_days",
            field=models.IntegerField(
                default=90,
                help_text="Finestra temporale per rilevamento ricorrenza (gg)",
            ),
        ),
        migrations.AddField(
            model_name="nis2configuration",
            name="recurrence_score_bonus",
            field=models.IntegerField(
                default=2,
                help_text="Punti aggiuntivi al PTNR se incidente ricorrente",
            ),
        ),
        migrations.AddField(
            model_name="nis2configuration",
            name="ptnr_threshold",
            field=models.IntegerField(
                default=4,
                help_text="PTNR minimo per classificare come significativo",
            ),
        ),
        migrations.AddField(
            model_name="nis2configuration",
            name="nis2_activity_description",
            field=models.TextField(
                blank=True,
                help_text="Descrizione attività NIS2 per i documenti formali",
            ),
        ),
    ]

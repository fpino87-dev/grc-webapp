from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plants", "0004_alter_plant_country"),
    ]

    operations = [
        migrations.AddField(
            model_name="plant",
            name="nis2_sector",
            field=models.CharField(
                blank=True,
                help_text="Settore NIS2 (es. Manifattura - Automotive) — usato in notifiche CSIRT",
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name="plant",
            name="nis2_subsector",
            field=models.CharField(
                blank=True,
                help_text="Sottosettore NIS2 — usato in notifiche formali NIS2",
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name="plant",
            name="legal_entity_name",
            field=models.CharField(
                blank=True,
                help_text="Ragione sociale per notifiche formali NIS2",
                max_length=300,
            ),
        ),
        migrations.AddField(
            model_name="plant",
            name="legal_entity_vat",
            field=models.CharField(
                blank=True,
                help_text="Partita IVA / VAT per notifiche formali NIS2",
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name="plant",
            name="nis2_activity_description",
            field=models.TextField(
                blank=True,
                help_text="Descrizione attività NIS2 del sito per documenti formali",
            ),
        ),
    ]

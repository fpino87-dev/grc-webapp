"""Porta i vecchi dati della formazione nel modello a evidenze.

Iscrizioni ed esiti phishing per persona diventano sessioni `legacy` con i soli
conteggi; `framework_refs` diventa il collegamento ai controlli. Le tabelle per
persona vengono eliminate dalla 0007. Anteprima senza modifiche: `manage.py check_training_migration_readiness`.
"""
from django.db import migrations


def forwards(apps, schema_editor):
    from apps.training.legacy import apply_legacy_migration, plan_legacy_migration

    TrainingCourse = apps.get_model("training", "TrainingCourse")
    plan = plan_legacy_migration(
        TrainingCourse,
        apps.get_model("training", "TrainingEnrollment"),
        apps.get_model("training", "PhishingSimulation"),
        apps.get_model("controls", "Control"),
        apps.get_model("plants", "Plant"),
    )
    apply_legacy_migration(plan, TrainingCourse, apps.get_model("training", "TrainingSession"))


def backwards(apps, schema_editor):
    apps.get_model("training", "TrainingSession").objects.filter(legacy=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("training", "0003_evidence_based_training"),
        ("controls", "0012_controlinstance_next_review_date_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

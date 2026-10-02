"""Ripulisce i cicli `legacy` vuoti creati dalla prima versione della 0015
(un ciclo per rischio invece che per sito). Soft delete: restano a storico.
Dove la 0015 corretta ha girato non trova nulla."""
from django.db import migrations
from django.utils import timezone


def forwards(apps, schema_editor):
    RiskAssessmentCycle = apps.get_model("risk", "RiskAssessmentCycle")
    RiskAssessment = apps.get_model("risk", "RiskAssessment")
    used = set(RiskAssessment.objects.order_by().values_list("cycle_id", flat=True).distinct())
    RiskAssessmentCycle.objects.filter(kind="legacy", deleted_at__isnull=True).exclude(pk__in=used).update(
        deleted_at=timezone.now(),
    )


class Migration(migrations.Migration):
    dependencies = [("risk", "0017_remove_previous_method")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]

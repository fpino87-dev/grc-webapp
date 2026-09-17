"""Crea i punti obbligatori §9.3.2 sui riesami esistenti non ancora approvati.

I riesami già approvati non vengono toccati: il loro verbale è chiuso.
"""
from django.db import migrations

CODES = [
    "azioni_precedenti", "contesto", "parti_interessate", "prestazioni",
    "feedback_parti", "rischi", "miglioramento",
]


def seed(apps, schema_editor):
    Review = apps.get_model("management_review", "ManagementReview")
    Item = apps.get_model("management_review", "ReviewAgendaItem")
    for review in Review.objects.filter(deleted_at__isnull=True).exclude(approval_status="approvato"):
        existing = set(Item.objects.filter(review=review).values_list("code", flat=True))
        Item.objects.bulk_create([
            Item(review=review, code=code, order=i, mandatory=True, created_by=review.created_by)
            for i, code in enumerate(CODES)
            if code not in existing
        ])


class Migration(migrations.Migration):
    dependencies = [("management_review", "0004_agenda_decisions_summary")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]

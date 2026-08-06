"""Rimuove il catalogo documenti obbligatori NIS2 generico.

NIS2 è una direttiva la cui documentazione dipende dalla trasposizione nazionale:
una lista fissa è fuorviante. Il framework generico "NIS2" non è attivo su alcun
sito (la compliance gira su "ACN_NIS2", trasposizione italiana), quindi queste
righe non erano nemmeno mostrate e non hanno agganci. Elimina solo le voci di
catalogo: i framework di controlli NIS2/ACN_NIS2 restano intatti.
"""
from django.db import migrations


def forwards(apps, schema_editor):
    RequiredDocument = apps.get_model("compliance_schedule", "RequiredDocument")
    RequiredDocument.objects.filter(framework="NIS2").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("compliance_schedule", "0004_fix_tisax_l3_required_docs"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]

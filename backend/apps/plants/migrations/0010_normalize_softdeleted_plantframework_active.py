"""Normalizza a active=False i PlantFramework soft-deleted.

Storicamente la rimozione di un framework da un plant faceva soft_delete() senza
azzerare `active`, lasciando record con deleted_at valorizzato ma active=True.
get_active_frameworks ora li esclude via deleted_at, ma per coerenza del dato li
portiamo a active=False. Idempotente.
"""
from django.db import migrations


def forwards(apps, schema_editor):
    PlantFramework = apps.get_model("plants", "PlantFramework")
    # Manager di default può filtrare i soft-deleted: usiamo il queryset base.
    PlantFramework.objects.filter(
        deleted_at__isnull=False, active=True
    ).update(active=False)


class Migration(migrations.Migration):

    dependencies = [
        ("plants", "0009_alter_plantframework_options"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]

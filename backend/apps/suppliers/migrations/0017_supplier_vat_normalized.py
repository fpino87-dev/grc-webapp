"""
Aggiunge `vat_normalized` (forma canonica della P.IVA) e lo popola per tutti i
fornitori, compresi gli eliminati.

Prima del vincolo di unicità (0018) verifica che tra i fornitori ATTIVI non ci
siano già P.IVA duplicate: se ce ne sono la migrazione si ferma elencandole,
così vanno unificate (o eliminate) a mano prima di rilanciare `migrate`.
"""
from collections import defaultdict

from django.db import migrations, models


def populate_and_check(apps, schema_editor):
    from apps.suppliers.normalization import normalize_vat

    Supplier = apps.get_model("suppliers", "Supplier")
    groups = defaultdict(list)
    for s in Supplier._base_manager.only("id", "name", "vat_number", "country", "deleted_at"):
        norm = normalize_vat(s.vat_number, s.country)
        Supplier._base_manager.filter(pk=s.pk).update(vat_normalized=norm)
        if norm and s.deleted_at is None:
            groups[norm].append(s)

    dupes = {k: v for k, v in groups.items() if len(v) > 1}
    if dupes:
        lines = [
            f"  P.IVA {vat}: " + "; ".join(f"{s.name} [{s.vat_number}] (id {s.pk})" for s in items)
            for vat, items in sorted(dupes.items())
        ]
        raise RuntimeError(
            "Fornitori attivi con la stessa P.IVA: unificarli (o eliminare i doppioni) "
            "prima di applicare il vincolo di unicità, poi rilanciare migrate.\n" + "\n".join(lines)
        )


class Migration(migrations.Migration):

    dependencies = [
        ("suppliers", "0016_supplier_evaluation_derived"),
    ]

    operations = [
        migrations.AddField(
            model_name="supplier",
            name="vat_normalized",
            field=models.CharField(blank=True, default="", editable=False, max_length=50),
        ),
        migrations.RunPython(populate_and_check, migrations.RunPython.noop),
    ]

"""Le due minacce di accesso remoto dei fornitori erano su due tipologie e la
Copertura chiedeva di valutare due volte lo stesso scenario. Ora FO_RMT vale
solo per i Fornitori e OT_RMT solo per l'OT: il catalogo si allinea e i rischi
del nuovo metodo registrati sull'altra tipologia si spostano, con valutazione,
misure e piano intatti. L'asset (FO_RMT) o il fornitore (OT_RMT) collegato,
che la nuova tipologia non prevede, resta nel testo "asset / gruppo" dello
scenario. Le dichiarazioni di non applicabilità rimaste doppie dopo lo
spostamento si archiviano (soft delete) se la coppia è già valutata o già
dichiarata. Il registro del metodo superato resta com'è."""
from django.db import migrations
from django.utils import timezone

TARGET = {"FO_RMT": "FORNITORI", "OT_RMT": "OT"}


def forwards(apps, schema_editor):
    Threat = apps.get_model("risk", "ThreatCatalogEntry")
    RiskAssessment = apps.get_model("risk", "RiskAssessment")
    for code, asset_type in TARGET.items():
        Threat.objects.filter(code=code, source="catalog").update(asset_types=[asset_type])
        risks = (RiskAssessment.objects.exclude(cycle__kind="legacy")
                 .filter(threat__code=code, deleted_at__isnull=True)
                 .exclude(asset_type=asset_type).select_related("asset", "supplier"))
        for risk in risks:
            linked = risk.asset if risk.asset_id and asset_type != "IT" else None
            linked = linked or (risk.supplier if risk.supplier_id and asset_type != "FORNITORI" else None)
            label = risk.asset_group_label or (linked.name if linked else "")
            RiskAssessment.objects.filter(pk=risk.pk).update(
                asset_type=asset_type, asset_group_label=label[:200],
                asset_id=None if asset_type == "FORNITORI" else risk.asset_id,
                supplier_id=None if asset_type == "OT" else risk.supplier_id,
            )
        # Una sola voce per coppia: via le non applicabilità doppie.
        current = RiskAssessment.objects.exclude(cycle__kind="legacy").filter(
            threat__code=code, asset_type=asset_type, deleted_at__isnull=True)
        for plant_id in set(current.values_list("plant_id", flat=True)):
            same = current.filter(plant_id=plant_id).order_by("-applicable", "created_at")
            keep = same.first()
            same.filter(applicable=False).exclude(pk=keep.pk).update(deleted_at=timezone.now())


class Migration(migrations.Migration):
    dependencies = [("risk", "0022_remove_class_override")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]

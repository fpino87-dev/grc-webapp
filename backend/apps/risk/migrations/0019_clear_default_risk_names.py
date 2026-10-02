"""Il nome del rischio non è più copiato dal titolo della minaccia (restava in
italiano per tutti): vuoto = titolo della minaccia nella lingua di chi guarda.
Svuota i nomi uguali a un titolo del catalogo, solo sui rischi del nuovo metodo;
i nomi scritti dagli utenti e il registro del metodo superato restano."""
from django.db import migrations


def forwards(apps, schema_editor):
    RiskAssessment = apps.get_model("risk", "RiskAssessment")
    risks = (
        RiskAssessment.objects.exclude(cycle__kind="legacy")
        .exclude(name="").filter(threat__isnull=False).select_related("threat")
    )
    for risk in risks:
        titles = {(v or {}).get("title", "").strip() for v in (risk.threat.translations or {}).values()}
        if risk.name.strip() in titles:
            risk.name = ""
            risk.save(update_fields=["name"])


class Migration(migrations.Migration):
    dependencies = [("risk", "0018_remove_empty_legacy_cycles")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]

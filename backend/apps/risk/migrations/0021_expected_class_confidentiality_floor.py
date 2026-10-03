"""La classe attesa ora rispetta la soglia di riservatezza (§7.2), come quella
attuale: ricalcola `expected_class` dei rischi del nuovo metodo. Cambia solo la
classe (dato derivato), non i valori inseriti; gli impatti attesi sotto la
soglia restano e li segnala la revisione di coerenza (expected_below_floor).
Il registro del metodo superato resta com'è."""
from django.db import migrations

from apps.risk.services import confidentiality_floor, risk_class


def forwards(apps, schema_editor):
    RiskAssessment = apps.get_model("risk", "RiskAssessment")
    risks = (
        RiskAssessment.objects.exclude(cycle__kind="legacy")
        .filter(threat__isnull=False, expected_impact__isnull=False)
        .select_related("threat").prefetch_related("information_classes")
    )
    for risk in risks:
        floor = None
        if "C" in (risk.threat.cia or []):
            floor = confidentiality_floor([ic.confidentiality for ic in risk.information_classes.all()])
        impact = max(int(risk.expected_impact), floor or 0)
        expected = risk_class(risk.expected_probability, impact) or ""
        if expected != risk.expected_class:
            RiskAssessment.objects.filter(pk=risk.pk).update(expected_class=expected)


class Migration(migrations.Migration):
    dependencies = [("risk", "0020_businessobjective_riskassessment_business_objectives")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]

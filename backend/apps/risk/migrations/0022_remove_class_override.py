"""Tolta la correzione manuale della classe: la classe attuale si legge solo
dalla matrice (impatto già comprensivo della soglia di riservatezza). Sui
rischi del nuovo metodo con una correzione la classe torna quella della
matrice; un'accettazione in corso o attiva su una classe diversa decade, come
quando la classe cambia per una nuova valutazione. Il registro del metodo
superato resta com'è."""
from django.db import migrations
from django.utils import timezone

REASON = "Correzione manuale della classe rimossa: la classe è ora quella della matrice."


def forwards(apps, schema_editor):
    RiskAssessment = apps.get_model("risk", "RiskAssessment")
    RiskAcceptance = apps.get_model("risk", "RiskAcceptance")
    for risk in RiskAssessment.objects.exclude(cycle__kind="legacy").exclude(class_override=0):
        if risk.current_class == risk.matrix_class:
            continue
        RiskAssessment.objects.filter(pk=risk.pk).update(current_class=risk.matrix_class)
        RiskAcceptance.objects.filter(risk_id=risk.pk, status__in=("pending", "active")) \
            .exclude(risk_class=risk.matrix_class) \
            .update(status="revoked", closed_at=timezone.now(), close_reason=REASON)


class Migration(migrations.Migration):
    dependencies = [("risk", "0021_expected_class_confidentiality_floor")]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.RemoveField(model_name="riskassessment", name="class_override"),
        migrations.RemoveField(model_name="riskassessment", name="override_rationale"),
    ]

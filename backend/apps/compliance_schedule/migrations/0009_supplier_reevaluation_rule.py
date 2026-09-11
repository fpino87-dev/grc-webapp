"""
La voce di scadenzario "Revisione contratti fornitori" (supplier_contract_review)
usava la data di valutazione del fornitore come se fosse una scadenza
contrattuale. Diventa "Rivalutazione fornitori" (supplier_reevaluation), basata
sulla scadenza della valutazione corrente: le regole già configurate nelle
policy (frequenza, preavviso, abilitazione) vengono conservate e rinominate.
"""
from django.db import migrations, models


def _rename(apps, old, new):
    ScheduleRule = apps.get_model("compliance_schedule", "ScheduleRule")
    ScheduleRule._base_manager.filter(rule_type=old).update(rule_type=new)


def forwards(apps, schema_editor):
    _rename(apps, "supplier_contract_review", "supplier_reevaluation")


def backwards(apps, schema_editor):
    _rename(apps, "supplier_reevaluation", "supplier_contract_review")


class Migration(migrations.Migration):

    dependencies = [
        ('compliance_schedule', '0008_alter_schedulerule_rule_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='schedulerule',
            name='rule_type',
            field=models.CharField(choices=[('control_review', 'Revisione controlli'), ('control_audit', 'Audit interno controlli'), ('document_policy', 'Revisione policy'), ('document_procedure', 'Revisione procedura'), ('document_record', 'Aggiornamento registro'), ('risk_assessment', 'Rivalutazione rischi'), ('risk_treatment', 'Revisione piano trattamento'), ('bcp_test', 'Test BCP/DR'), ('bcp_review', 'Revisione piano BCP'), ('incident_review', 'Revisione incidenti chiusi'), ('supplier_assessment', 'Assessment fornitori'), ('supplier_reevaluation', 'Rivalutazione fornitori'), ('asset_maintenance', 'Manutenzione impianti e apparati'), ('training_mandatory', 'Formazione obbligatoria'), ('training_refresh', 'Aggiornamento formazione'), ('management_review', 'Revisione della direzione'), ('security_committee', 'Riunione comitato sicurezza'), ('finding_minor', 'Risoluzione non conformità minore'), ('finding_major', 'Risoluzione non conformità maggiore'), ('finding_observation', 'Risoluzione osservazione'), ('pdca_cycle', 'Ciclo PDCA'), ('kpi_review', 'Revisione KPI'), ('isms_review', 'Revisione ISMS annuale')], max_length=50),
        ),
        migrations.RunPython(forwards, backwards),
    ]

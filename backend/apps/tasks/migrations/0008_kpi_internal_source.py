from django.db import migrations, models


# Codici KPI che ora si popolano via connettore interno (source="internal").
# Inlined nella migrazione per renderla autoconsistente e indipendente da
# evoluzioni future di kpi_connectors.INTERNAL_CONNECTORS.
INTERNAL_KPI_CODES = [
    "controls_compliance_rate",
    "evidence_expiry_rate",
    "open_pdca_over_90days",
    "audit_findings_open_rate",
    "training_completion_rate",
    "systems_eol_count",
    "incident_mttr_hours",
    "incident_recurrence_rate",
    "incident_rca_completion_rate",
    "suppliers_assessed_rate",
    "suppliers_critical_unassessed",
]

SOURCE_CHOICES = [
    ("checklist", "Checklist"),
    ("internal", "Modulo interno (auto-calcolo)"),
    ("api", "API esterna"),
    ("manual", "Inserimento manuale"),
]


def set_internal_source(apps, schema_editor):
    """Le KPIDefinition già importate per questi codici erano source='api'
    (push esterno mai arrivato): le riportiamo a 'internal' così il task
    settimanale le calcola dai moduli. Tocchiamo solo source='api' per non
    sovrascrivere eventuali definizioni configurate manualmente in altro modo."""
    KPIDefinition = apps.get_model("tasks", "KPIDefinition")
    KPIDefinition.objects.filter(
        kpi_code__in=INTERNAL_KPI_CODES, source="api"
    ).update(source="internal")


def revert_internal_source(apps, schema_editor):
    KPIDefinition = apps.get_model("tasks", "KPIDefinition")
    KPIDefinition.objects.filter(
        kpi_code__in=INTERNAL_KPI_CODES, source="internal"
    ).update(source="api")


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0007_checklisttemplate_days_of_week"),
    ]

    operations = [
        migrations.AlterField(
            model_name="kpidefinition",
            name="source",
            field=models.CharField(
                choices=SOURCE_CHOICES, db_index=True, default="checklist", max_length=15
            ),
        ),
        migrations.AlterField(
            model_name="operationalkpisnapshot",
            name="source",
            field=models.CharField(
                choices=SOURCE_CHOICES, default="checklist", max_length=15
            ),
        ),
        migrations.RunPython(set_internal_source, revert_internal_source),
    ]

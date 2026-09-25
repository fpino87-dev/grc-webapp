from django.db import migrations


def sync_audit_subtype(apps, schema_editor):
    """Riallinea il tipo di audit dei PDCA collegati ai finding a quello
    dell'audit: fino a questa versione, cambiando il tipo di un audit, i PDCA
    già aperti dai suoi finding restavano con il tipo precedente."""
    AuditFinding = apps.get_model("audit_prep", "AuditFinding")
    PdcaCycle = apps.get_model("pdca", "PdcaCycle")
    rows = (
        AuditFinding.objects.filter(pdca_cycle__isnull=False)
        .values_list("pdca_cycle_id", "audit_prep__audit_type")
    )
    for cycle_id, audit_type in rows:
        PdcaCycle.objects.filter(pk=cycle_id).exclude(audit_subtype=audit_type).update(
            audit_subtype=audit_type,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("pdca", "0007_alter_pdcacycle_plant"),
        ("audit_prep", "0011_external_consultant_full_coverage"),
    ]

    operations = [
        migrations.RunPython(sync_audit_subtype, migrations.RunPython.noop),
    ]

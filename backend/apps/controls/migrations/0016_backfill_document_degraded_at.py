from django.db import migrations

# Eventi dell'audit trail che decidono lo stato di un controllo: il più recente
# dice chi ha messo il controllo nello stato in cui si trova.
STATUS_EVENTS = (
    "control.evidence_expired",
    "control.evaluated",
    "control.propagated",
    "control.applicability_changed",
    "control.restored_compliant",
)


def backfill(apps, schema_editor):
    """Una tantum: segna i controlli già scesi a Parziale per il degrado
    automatico notturno, così il ripristino a Compliant vale anche per loro.

    Si legge l'audit trail (sola lettura): il controllo è candidato se l'ultimo
    evento che ne ha deciso lo stato è il degrado automatico senza evidenze
    scadute e nessuno lo ha rivalutato dopo. Qui si scrive solo il segnale: lo
    stato lo ripristina il task notturno, e solo se documenti ed evidenze
    risultano di nuovo tutti a posto (con la sua riga di audit trail).
    """
    ControlInstance = apps.get_model("controls", "ControlInstance")
    AuditLog = apps.get_model("core", "AuditLog")

    candidates = ControlInstance.objects.filter(
        status="parziale",
        deleted_at__isnull=True,
        document_degraded_at__isnull=True,
    ).only("id", "last_evaluated_at")

    for instance in candidates:
        last = (
            AuditLog.objects.filter(
                entity_type="controlinstance",
                entity_id=instance.pk,
                action_code__in=STATUS_EVENTS,
            )
            .order_by("-timestamp_utc")
            .first()
        )
        if last is None or last.action_code != "control.evidence_expired":
            continue
        if (last.payload or {}).get("has_expired_evidences") is not False:
            continue
        if instance.last_evaluated_at and instance.last_evaluated_at > last.timestamp_utc:
            continue
        ControlInstance.objects.filter(pk=instance.pk).update(
            document_degraded_at=last.timestamp_utc
        )


class Migration(migrations.Migration):

    dependencies = [
        ("controls", "0015_controlinstance_document_degraded_at"),
        ("core", "0004_auditlog_hash_version_alter_auditlog_timestamp_utc"),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]

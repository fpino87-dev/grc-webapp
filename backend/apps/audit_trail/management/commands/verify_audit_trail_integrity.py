import sys

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Verifica integrità hash chain AuditLog (per-record + linkage di catena) e presenza trigger anti-tamper"

    def add_arguments(self, parser):
        parser.add_argument("--since", type=str, help="Data ISO es. 2024-01-01")
        parser.add_argument("--verbose", action="store_true")

    def handle(self, *args, **options):
        from core.audit import AuditLog, audit_trigger_installed, verify_audit_integrity

        # Verifica preliminare: il trigger anti-tamper deve essere installato.
        if not audit_trigger_installed():
            self.stderr.write(
                self.style.ERROR(
                    "ATTENZIONE: trigger 'audit_no_mutation' assente — l'audit "
                    "log NON è protetto da UPDATE/DELETE. Riapplicare migrazione "
                    "core/0002_audit_trigger."
                )
            )
            sys.exit(2)

        qs = AuditLog.objects.all()
        if options["since"]:
            qs = qs.filter(timestamp_utc__date__gte=options["since"])

        result = verify_audit_integrity(qs)
        if not result["ok"]:
            self.stderr.write(
                self.style.ERROR(
                    f"CORROTTO [{result['error']}]: {result.get('message', '')} "
                    f"(record={result.get('record_id', '—')}, "
                    f"entity_type={result.get('entity_type', '—')})"
                )
            )
            sys.exit(1)

        self.stdout.write(
            self.style.SUCCESS(
                f"Audit trail integrity OK — {result['v1']} record v1 (legacy) + "
                f"{result['v2']} record v2 (tamper-evident esteso); "
                f"linkage di catena verificata su {result['checked']} record."
            )
        )

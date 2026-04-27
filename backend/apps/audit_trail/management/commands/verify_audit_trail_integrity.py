import sys

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Verifica integrità hash chain AuditLog (v1 e v2) e presenza trigger anti-tamper"

    def add_arguments(self, parser):
        parser.add_argument("--since", type=str, help="Data ISO es. 2024-01-01")
        parser.add_argument("--verbose", action="store_true")

    def handle(self, *args, **options):
        from core.audit import AuditLog, compute_record_hash

        # Verifica preliminare: il trigger anti-tamper deve essere installato.
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_trigger WHERE tgname = 'audit_no_mutation' LIMIT 1;"
            )
            if cursor.fetchone() is None:
                self.stderr.write(
                    self.style.ERROR(
                        "ATTENZIONE: trigger 'audit_no_mutation' assente — l'audit "
                        "log NON è protetto da UPDATE/DELETE. Riapplicare migrazione "
                        "core/0002_audit_trigger."
                    )
                )
                sys.exit(2)

        qs = AuditLog.objects.order_by("timestamp_utc")
        if options["since"]:
            qs = qs.filter(timestamp_utc__date__gte=options["since"])

        v1_count = 0
        v2_count = 0
        for i, log in enumerate(qs):
            expected = compute_record_hash(log)
            if expected != log.record_hash:
                self.stderr.write(
                    self.style.ERROR(
                        f"CORROTTO: id={log.id} azione={log.action_code} "
                        f"hash_version={log.hash_version}"
                    )
                )
                sys.exit(1)
            if log.hash_version == "v2":
                v2_count += 1
            else:
                v1_count += 1
            if options["verbose"]:
                self.stdout.write(f"OK [{i + 1}] {log.action_code} ({log.hash_version})")

        self.stdout.write(
            self.style.SUCCESS(
                f"Audit trail integrity OK — {v1_count} record v1 (legacy) + "
                f"{v2_count} record v2 (tamper-evident esteso)"
            )
        )


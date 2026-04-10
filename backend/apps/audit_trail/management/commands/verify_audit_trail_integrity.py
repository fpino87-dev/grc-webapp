import hashlib
import json
import sys

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Verifica integrità hash chain AuditLog"

    def add_arguments(self, parser):
        parser.add_argument("--since", type=str, help="Data ISO es. 2024-01-01")
        parser.add_argument("--verbose", action="store_true")

    def handle(self, *args, **options):
        from core.audit import AuditLog

        qs = AuditLog.objects.order_by("timestamp_utc")
        if options["since"]:
            qs = qs.filter(timestamp_utc__date__gte=options["since"])
        prev_hash = "0" * 64
        for i, log in enumerate(qs):
            content = json.dumps(log.payload, sort_keys=True, default=str) + log.prev_hash
            expected = hashlib.sha256(content.encode()).hexdigest()
            if expected != log.record_hash:
                self.stderr.write(
                    self.style.ERROR(
                        f"CORROTTO: id={log.id} azione={log.action_code}",
                    )
                )
                sys.exit(1)
            if options["verbose"]:
                self.stdout.write(f"OK [{i + 1}] {log.action_code}")
            prev_hash = log.record_hash
        self.stdout.write(
            self.style.SUCCESS(
                f"Audit trail integrity OK — {qs.count()} records verificati",
            )
        )


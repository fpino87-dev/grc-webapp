"""Backfill OsintFinding per scan storici precedenti all'integrazione del finding engine.

Per ogni entità attiva con almeno uno scan completato, esegue `sync_findings`
sull'ultimo scan completato. Idempotente: se i finding esistono già verranno
aggiornati (last_seen, params, severity) invece di duplicati.
"""
from django.core.management.base import BaseCommand

from apps.osint.findings import sync_findings
from apps.osint.models import OsintEntity, OsintScan, ScanStatus


class Command(BaseCommand):
    help = "Genera i finding mancanti per gli scan storici già presenti nel DB."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra cosa verrebbe fatto senza scrivere nel DB.",
        )

    def handle(self, *args, **opts):
        dry = opts.get("dry_run", False)
        total_c = total_u = total_r = 0
        processed = 0

        for entity in OsintEntity.objects.filter(is_active=True, deleted_at__isnull=True):
            last_scan = (
                OsintScan.objects.filter(
                    entity=entity,
                    status=ScanStatus.COMPLETED,
                    deleted_at__isnull=True,
                )
                .order_by("-scan_date")
                .first()
            )
            if not last_scan:
                continue

            if dry:
                self.stdout.write(f"[dry] {entity.domain}: scan {last_scan.scan_date}")
                processed += 1
                continue

            c, u, r = sync_findings(entity, last_scan)
            total_c += c
            total_u += u
            total_r += r
            processed += 1
            self.stdout.write(f"  {entity.domain}: created={c} updated={u} resolved={r}")

        self.stdout.write(self.style.SUCCESS(
            f"Processate {processed} entità — created={total_c} updated={total_u} resolved={total_r}"
        ))

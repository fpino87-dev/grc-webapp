"""Retention scan storici OSINT.

Politica di retention bilanciata tra utilità per audit e dimensione DB:
- ULTIMI 52 SCAN per entità (≈ 1 anno di scansioni settimanali)
- + 1 SCAN PER MESE per gli scan più vecchi di 52 settimane (12 mesi storici)

Tutto il resto viene soft-deleted. Non vengono mai cancellati scan referenziati
da finding aperti (la FK è SET_NULL, ma se un finding li referenzia preferiamo
mantenere lo storico).

Idempotente: se non c'è nulla da cancellare il comando esce a 0.
"""
from collections import defaultdict
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.osint.models import (
    FindingStatus,
    OsintEntity,
    OsintFinding,
    OsintScan,
)


class Command(BaseCommand):
    help = "Soft-delete scan OSINT vecchi mantenendo: 52 settimanali + 12 mensili per entità."

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep-recent",
            type=int,
            default=52,
            help="Numero di scan recenti da mantenere per entità (default 52).",
        )
        parser.add_argument(
            "--keep-monthly",
            type=int,
            default=12,
            help="Numero di mesi storici da campionare (1 scan/mese, default 12).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra cosa verrebbe eliminato senza scrivere nel DB.",
        )

    def handle(self, *args, **opts):
        keep_recent = max(1, opts["keep_recent"])
        keep_monthly = max(0, opts["keep_monthly"])
        dry = opts["dry_run"]
        now = timezone.now()
        monthly_cutoff = now - timedelta(weeks=keep_recent)

        # Scan referenziati da finding ancora aperti: protetti.
        protected_ids = set(
            OsintFinding.objects.filter(
                status__in=[
                    FindingStatus.OPEN,
                    FindingStatus.ACKNOWLEDGED,
                    FindingStatus.IN_PROGRESS,
                ],
                deleted_at__isnull=True,
                scan__isnull=False,
            ).values_list("scan_id", flat=True)
        )

        total_kept = 0
        total_deleted = 0
        per_entity_report: list[str] = []

        for entity in OsintEntity.objects.all():
            scans = list(
                OsintScan.objects.filter(entity=entity, deleted_at__isnull=True)
                .order_by("-scan_date")
                .only("id", "scan_date")
            )
            if not scans:
                continue

            keep_ids: set = set(s.id for s in scans[:keep_recent])

            # Per gli scan più vecchi del cutoff, tieni 1 per (anno, mese).
            older = [s for s in scans[keep_recent:]]
            seen_months: dict[tuple[int, int], int] = {}
            for s in older:
                ym = (s.scan_date.year, s.scan_date.month)
                if ym not in seen_months and len(seen_months) < keep_monthly:
                    seen_months[ym] = 1
                    keep_ids.add(s.id)

            keep_ids |= protected_ids  # safety net

            to_delete = [s for s in scans if s.id not in keep_ids]
            total_kept += len(scans) - len(to_delete)
            total_deleted += len(to_delete)

            if to_delete:
                per_entity_report.append(
                    f"  {entity.domain}: kept={len(scans) - len(to_delete)} delete={len(to_delete)}"
                )
                if not dry:
                    with transaction.atomic():
                        for s in to_delete:
                            s.deleted_at = now
                            s.save(update_fields=["deleted_at", "updated_at"])

        for line in per_entity_report:
            self.stdout.write(line)

        verb = "[dry] would delete" if dry else "soft-deleted"
        self.stdout.write(self.style.SUCCESS(
            f"OSINT cleanup: kept={total_kept} {verb}={total_deleted} "
            f"(policy: {keep_recent} recenti + {keep_monthly} mensili, cutoff {monthly_cutoff:%Y-%m-%d})"
        ))

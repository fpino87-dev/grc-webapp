"""Celery tasks modulo OSINT — Step 6.

OsintWeeklyScanner: ogni lunedì alle 02:00.
run_entity_scan: task singolo per "forza rescan" sincrono.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=60,
    max_retries=2,
    name="osint.weekly_scan",
)
def run_weekly_scan(self):
    """Scansiona tutte le entità attive rispettando la frequenza configurata."""
    from apps.osint.models import OsintEntity, OsintSettings
    from apps.osint.services import aggregate_entities
    from apps.osint.enrichers.run import run_enrichment

    # Sincronizza prima le entità dai moduli sorgente
    agg = aggregate_entities()
    logger.info("OSINT pre-scan aggregation: %s", agg)

    settings = OsintSettings.load()
    now = timezone.now()

    entities = OsintEntity.objects.filter(is_active=True, deleted_at__isnull=True)
    total = entities.count()
    scanned = 0
    skipped = 0
    errors = 0

    for entity in entities:
        try:
            if _should_scan(entity, now):
                run_enrichment(entity, settings)
                scanned += 1
            else:
                skipped += 1
        except Exception as exc:
            logger.error("OSINT scan failed for %s: %s", entity.domain, exc)
            errors += 1

    logger.info(
        "OSINT weekly scan complete — total=%d scanned=%d skipped=%d errors=%d",
        total, scanned, skipped, errors,
    )
    return {"total": total, "scanned": scanned, "skipped": skipped, "errors": errors}


def _should_scan(entity, now) -> bool:
    """True se l'entità deve essere scansionata ora in base alla frequenza."""
    from apps.osint.models import OsintScan, ScanFrequency
    if entity.scan_frequency == ScanFrequency.WEEKLY:
        return True
    # Monthly: solo se l'ultimo scan è più vecchio di 28 giorni
    last = (
        OsintScan.objects.filter(entity=entity)
        .order_by("-scan_date")
        .values_list("scan_date", flat=True)
        .first()
    )
    if last is None:
        return True
    return (now - last).days >= 28


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=30,
    max_retries=1,
    name="osint.scan_entity",
)
def run_entity_scan(self, entity_id: str):
    """Scan immediato su una singola entità — chiamato da "Forza rescan" in UI."""
    from apps.osint.models import OsintEntity, OsintSettings

    try:
        entity = OsintEntity.objects.get(pk=entity_id, is_active=True, deleted_at__isnull=True)
    except OsintEntity.DoesNotExist:
        logger.warning("OSINT entity %s not found for on-demand scan", entity_id)
        return {"error": "entity_not_found"}

    settings = OsintSettings.load()
    from apps.osint.enrichers.run import run_enrichment
    scan = run_enrichment(entity, settings)
    return {"scan_id": str(scan.pk), "status": scan.status, "score": scan.score_total}

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
    """Pianifica la scansione delle entità attive rispettando la frequenza.

    Fa **fan-out**: invia un task `run_entity_scan` per ogni entità da scansionare
    invece di scansionarle in serie in un unico task (review #6). Vantaggi:
    - il fallimento/retry di una singola entità non ri-scansiona tutte le altre
      (niente quota API sprecata su VirusTotal/AbuseIPDB al retry);
    - le attese del throttle avvengono in worker paralleli, non bloccano un
      singolo worker per tutta la durata;
    - il throttle Redis (token bucket per bucket) continua a serializzare i call
      rate verso ciascuna sorgente esterna anche tra worker diversi.
    """
    from apps.osint.models import OsintEntity
    from apps.osint.services import aggregate_entities

    # Sincronizza prima le entità dai moduli sorgente
    agg = aggregate_entities()
    logger.info("OSINT pre-scan aggregation: %s", agg)

    now = timezone.now()
    entities = OsintEntity.objects.filter(is_active=True, deleted_at__isnull=True)
    total = entities.count()

    # De-dup per dominio: raggruppa le entità *da scansionare ora* per dominio.
    # Le entità che condividono un dominio vengono affidate a un unico
    # `run_domain_scan` che esegue l'enrichment esterno una sola volta e propaga
    # i dati domain-level alle altre (ricalcolando score/alert/finding per entità).
    from collections import defaultdict
    due_by_domain: dict[str, list] = defaultdict(list)
    skipped = 0
    for entity in entities:
        if _should_scan(entity, now):
            due_by_domain[entity.domain].append(entity)
        else:
            skipped += 1

    dispatched = 0
    deduped_domains = 0
    for domain, ents in due_by_domain.items():
        if len(ents) == 1:
            run_entity_scan.delay(str(ents[0].pk))
        else:
            run_domain_scan.delay(domain, [str(e.pk) for e in ents])
            deduped_domains += 1
        dispatched += len(ents)

    logger.info(
        "OSINT weekly scan planned — total=%d dispatched=%d skipped=%d deduped_domains=%d",
        total, dispatched, skipped, deduped_domains,
    )
    return {
        "total": total,
        "dispatched": dispatched,
        "skipped": skipped,
        "deduped_domains": deduped_domains,
    }


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


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=30,
    max_retries=1,
    name="osint.scan_domain",
)
def run_domain_scan(self, domain: str, entity_ids: list[str]):
    """Scansiona più entità che condividono lo stesso dominio con una sola
    chiamata di enrichment esterno (de-dup quota API).

    Esegue l'enrichment completo su un'entità "primaria" (preferendo una
    `my_domain`, così dnstwist/HIBP girano), poi propaga i dati domain-level alle
    altre entità ricalcolando per ciascuna score/alert/finding.
    """
    from apps.osint.models import EntityType, OsintEntity, OsintSettings
    from apps.osint.enrichers.run import run_enrichment, _propagate_scan

    entities = list(
        OsintEntity.objects.filter(pk__in=entity_ids, is_active=True, deleted_at__isnull=True)
    )
    if not entities:
        logger.warning("OSINT domain scan %s: nessuna entità attiva tra %s", domain, entity_ids)
        return {"error": "no_entities", "domain": domain}

    # Primaria: preferisci una my_domain (HIBP/dnstwist sono my_domain-only).
    primary = next((e for e in entities if e.entity_type == EntityType.MY_DOMAIN), entities[0])
    others = [e for e in entities if e.pk != primary.pk]

    settings = OsintSettings.load()
    primary_scan = run_enrichment(primary, settings)

    propagated = 0
    for ent in others:
        _propagate_scan(ent, primary_scan, settings)
        propagated += 1

    logger.info(
        "OSINT domain scan %s — primary=%s status=%s propagated=%d",
        domain, primary.pk, primary_scan.status, propagated,
    )
    return {
        "domain": domain,
        "primary": str(primary.pk),
        "status": primary_scan.status,
        "propagated": propagated,
    }

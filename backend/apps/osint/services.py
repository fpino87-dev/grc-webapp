"""Business logic modulo OSINT.

Aggregator (Step 2): legge dagli altri moduli e popola `OsintEntity`.
Nessuna logica di enrichment o scoring qui — vedi `enrichers/`, `scoring.py`, `alerts.py`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlparse

from django.db import transaction

from apps.assets.models import AssetIT, AssetOT, AssetSW
from apps.plants.models import Plant
from apps.suppliers.models import Supplier

from .models import (
    EntityType,
    OsintEntity,
    OsintSettings,
    ScanFrequency,
    SourceModule,
)

logger = logging.getLogger(__name__)


def extract_domain(raw: str | None) -> str:
    """Estrae l'hostname (lowercase) da una URL o stringa dominio.

    Esempi:
      "https://example.com/path" → "example.com"
      "example.COM" → "example.com"
      "" → ""
      None → ""
    """
    if not raw:
        return ""
    value = raw.strip()
    if not value:
        return ""
    if "://" not in value:
        value = "http://" + value
    try:
        host = urlparse(value).hostname or ""
    except ValueError:
        return ""
    return host.lower().rstrip(".")


@dataclass
class AggregationResult:
    created: int = 0
    updated: int = 0
    reactivated: int = 0
    deactivated: int = 0

    def add(self, other: "AggregationResult") -> "AggregationResult":
        self.created += other.created
        self.updated += other.updated
        self.reactivated += other.reactivated
        self.deactivated += other.deactivated
        return self


def _upsert_entity(
    *,
    source_module: str,
    source_id,
    domain: str,
    entity_type: str,
    display_name: str,
    is_nis2_critical: bool,
    scan_frequency: str,
    result: AggregationResult,
    kept: set,
) -> None:
    domain = domain.strip().lower()
    if not domain:
        return
    entity, created = OsintEntity.objects.get_or_create(
        source_module=source_module,
        source_id=source_id,
        domain=domain,
        defaults={
            "entity_type": entity_type,
            "display_name": display_name,
            "is_nis2_critical": is_nis2_critical,
            "scan_frequency": scan_frequency,
            "is_active": True,
        },
    )
    if created:
        result.created += 1
    else:
        changed = False
        if entity.entity_type != entity_type:
            entity.entity_type = entity_type
            changed = True
        if entity.display_name != display_name:
            entity.display_name = display_name
            changed = True
        if entity.is_nis2_critical != is_nis2_critical:
            entity.is_nis2_critical = is_nis2_critical
            changed = True
        if entity.scan_frequency != scan_frequency:
            entity.scan_frequency = scan_frequency
            changed = True
        if not entity.is_active:
            entity.is_active = True
            result.reactivated += 1
            changed = True
        if changed:
            entity.save()
            result.updated += 1
    kept.add(entity.pk)


def _deactivate_missing(source_module: str, kept: set, result: AggregationResult) -> None:
    qs = OsintEntity.objects.filter(source_module=source_module, is_active=True).exclude(pk__in=kept)
    count = qs.count()
    if count:
        qs.update(is_active=False)
        result.deactivated += count


def _sync_plants(settings: OsintSettings, result: AggregationResult) -> None:
    kept: set = set()
    for plant in Plant.objects.all():  # soft-delete manager filtra già deleted_at
        domains: list[str] = []
        if plant.domain:
            domains.append(plant.domain)
        for d in plant.additional_domains or []:
            if d:
                domains.append(d)
        for raw in domains:
            domain = extract_domain(raw)
            if not domain:
                continue
            _upsert_entity(
                source_module=SourceModule.SITES,
                source_id=plant.id,
                domain=domain,
                entity_type=EntityType.MY_DOMAIN,
                display_name=plant.name,
                is_nis2_critical=plant.is_nis2_subject,
                scan_frequency=settings.freq_my_domains,
                result=result,
                kept=kept,
            )
    _deactivate_missing(SourceModule.SITES, kept, result)


def _sync_suppliers(settings: OsintSettings, result: AggregationResult) -> None:
    kept: set = set()
    for sup in Supplier.objects.all():
        domain = extract_domain(sup.website)
        if not domain:
            continue
        is_nis2 = bool(getattr(sup, "nis2_relevant", False))
        freq = settings.freq_suppliers_critical if is_nis2 else settings.freq_suppliers_other
        _upsert_entity(
            source_module=SourceModule.SUPPLIERS,
            source_id=sup.id,
            domain=domain,
            entity_type=EntityType.SUPPLIER,
            display_name=sup.name,
            is_nis2_critical=is_nis2,
            scan_frequency=freq,
            result=result,
            kept=kept,
        )
    _deactivate_missing(SourceModule.SUPPLIERS, kept, result)


def _sync_assets_it(settings: OsintSettings, result: AggregationResult) -> None:
    kept: set = set()
    for a in AssetIT.objects.select_related("plant").all():
        candidates: list[str] = []
        if a.fqdn:
            candidates.append(a.fqdn)
        if a.ip_address:
            candidates.append(str(a.ip_address))
        for raw in candidates:
            domain = extract_domain(raw)
            if not domain:
                continue
            _upsert_entity(
                source_module=SourceModule.ASSETS_IT,
                source_id=a.id,
                domain=domain,
                entity_type=EntityType.ASSET,
                display_name=a.name,
                is_nis2_critical=False,
                scan_frequency=settings.freq_my_domains,
                result=result,
                kept=kept,
            )
    _deactivate_missing(SourceModule.ASSETS_IT, kept, result)


def _sync_assets_ot(settings: OsintSettings, result: AggregationResult) -> None:
    """AssetOT attualmente non ha campi di rete esposti pubblicamente.
    Placeholder per estensioni future — deattiva tutto in assenza di sorgente.
    """
    kept: set = set()
    # Nessun campo pubblico da cui estrarre dominio/IP nel modello corrente.
    # Se/quando AssetOT acquisirà fqdn/ip_address, aggiungere logica qui.
    _ = AssetOT.objects.all().exists()  # touch per coerenza
    _deactivate_missing(SourceModule.ASSETS_OT, kept, result)


def _sync_assets_software(settings: OsintSettings, result: AggregationResult) -> None:
    kept: set = set()
    for sw in AssetSW.objects.select_related("plant").all():
        domain = extract_domain(sw.vendor_url)
        if not domain:
            continue
        _upsert_entity(
            source_module=SourceModule.ASSETS_SOFTWARE,
            source_id=sw.id,
            domain=domain,
            entity_type=EntityType.SUPPLIER,  # vendor software = fornitore ai fini OSINT
            display_name=f"{sw.vendor or sw.name} ({sw.name})" if sw.vendor else sw.name,
            is_nis2_critical=False,
            scan_frequency=settings.freq_suppliers_other,
            result=result,
            kept=kept,
        )
    _deactivate_missing(SourceModule.ASSETS_SOFTWARE, kept, result)


@transaction.atomic
def aggregate_entities() -> AggregationResult:
    """Sincronizza `osint_entities` leggendo da tutti i moduli sorgente.

    Idempotente. Chiamabile ad ogni scan e all'apertura della dashboard OSINT.
    """
    settings = OsintSettings.load()
    result = AggregationResult()
    _sync_plants(settings, result)
    _sync_suppliers(settings, result)
    _sync_assets_it(settings, result)
    _sync_assets_ot(settings, result)
    _sync_assets_software(settings, result)
    logger.info(
        "OSINT aggregation completed: created=%d updated=%d reactivated=%d deactivated=%d",
        result.created, result.updated, result.reactivated, result.deactivated,
    )
    return result


def find_duplicates() -> dict[str, list[OsintEntity]]:
    """Ritorna domini presenti su più entità (più sorgenti) — per banner UI.

    Chiave: dominio; valore: lista entità attive che condividono il dominio.
    """
    from collections import defaultdict
    buckets: dict[str, list[OsintEntity]] = defaultdict(list)
    for e in OsintEntity.objects.filter(is_active=True):
        buckets[e.domain].append(e)
    return {d: items for d, items in buckets.items() if len(items) > 1}

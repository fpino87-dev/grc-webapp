"""Signal handlers OSINT.

Due responsabilità:
1. Mantenere aggiornati i campi denormalizzati su OsintEntity (last_scan_at,
   last_score_total, active_alerts_count_cached) per eliminare N+1 nelle viste.
2. Sincronizzare le entità OSINT quando le sorgenti (Plant/Supplier/Asset) cambiano,
   senza richiedere chiamate manuali ad aggregate_entities() ad ogni dashboard load.

Tutti i signal sono best-effort: un fallimento NON deve rompere il salvataggio
dell'entità sorgente, perché OSINT è un modulo "passivo" sul core GRC.
"""
from __future__ import annotations

import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cache denormalizzata su OsintEntity
# ---------------------------------------------------------------------------

@receiver(post_save, sender="osint.OsintScan")
def _update_entity_scan_cache(sender, instance, **kwargs):
    if instance.status != "completed":
        return
    from apps.osint.models import OsintEntity, OsintScan

    # Recupera il penultimo completato per popolare prev_score_total (delta).
    prev = (
        OsintScan.objects.filter(entity_id=instance.entity_id, status="completed")
        .exclude(pk=instance.pk)
        .order_by("-scan_date")
        .values_list("score_total", flat=True)
        .first()
    )
    OsintEntity.objects.filter(pk=instance.entity_id).update(
        last_scan_at=instance.scan_date,
        last_score_total=instance.score_total,
        prev_score_total=prev,
    )


@receiver(post_save, sender="osint.OsintAlert")
@receiver(post_delete, sender="osint.OsintAlert")
def _update_entity_alerts_cache(sender, instance, **kwargs):
    from apps.osint.models import OsintAlert, OsintEntity
    count = OsintAlert.objects.filter(
        entity_id=instance.entity_id,
        status__in=["new", "acknowledged"],
        deleted_at__isnull=True,
    ).count()
    OsintEntity.objects.filter(pk=instance.entity_id).update(active_alerts_count_cached=count)


# ---------------------------------------------------------------------------
# Sync entità da sorgenti (best-effort, non bloccante)
# ---------------------------------------------------------------------------

def _safe_sync():
    """Esegue aggregate_entities dopo il commit della transazione corrente.

    on_commit garantisce: (a) niente sync se la tx fa rollback (es. errore di
    salvataggio della sorgente), (b) i test transactional non scatenano
    sync sincroni (Django fa rollback alla fine del test). In produzione
    è equivalente a "aspetta il commit e poi sincronizza" — esattamente
    il comportamento corretto.
    """
    from django.db import transaction

    def _do():
        try:
            from apps.osint.services import aggregate_entities
            aggregate_entities()
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning("OSINT aggregator failed via signal: %s", exc)

    transaction.on_commit(_do)


@receiver(post_save, sender="plants.Plant")
@receiver(post_delete, sender="plants.Plant")
def _sync_on_plant_change(sender, **kwargs):
    _safe_sync()


@receiver(post_save, sender="suppliers.Supplier")
@receiver(post_delete, sender="suppliers.Supplier")
def _sync_on_supplier_change(sender, **kwargs):
    _safe_sync()


@receiver(post_save, sender="assets.AssetIT")
@receiver(post_delete, sender="assets.AssetIT")
def _sync_on_asset_it_change(sender, **kwargs):
    _safe_sync()


@receiver(post_save, sender="assets.AssetSW")
@receiver(post_delete, sender="assets.AssetSW")
def _sync_on_asset_sw_change(sender, **kwargs):
    _safe_sync()

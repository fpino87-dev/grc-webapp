"""Celery task del Centro Operativo (M21)."""
from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="cockpit.sync")
def sync_cockpit():
    """Riconcilia lo stato degli insight (auto-resolve) e salva lo snapshot della
    postura per il trend. Schedulato settimanalmente dopo i ricalcoli del lunedì."""
    from apps.cockpit.services import sync_insights, record_posture_snapshot

    synced = sync_insights()
    snapshots = record_posture_snapshot()
    logger.info("Cockpit sync: %s, snapshots=%d", synced, snapshots)
    return {"synced": synced, "snapshots": snapshots}

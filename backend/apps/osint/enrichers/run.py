"""Orchestratore enrichment OSINT.

Chiama tutti gli enricher in sequenza, rispetta rate limit, salva OsintScan.
Se almeno un enricher ha successo → status = 'completed'.
Se tutti falliscono → status = 'failed'.
"""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from apps.osint.models import OsintEntity, OsintSettings

logger = logging.getLogger(__name__)

# Secondi di pausa DOPO ogni chiamata alle API con rate limit
DELAY_CRTSH_VT = 15      # crt.sh e VirusTotal: 4/min free
DELAY_ABUSE_OTX = 5      # AbuseIPDB e OTX: più generosi
DELAY_GSB = 2
DELAY_HIBP = 5


def run_enrichment(entity: "OsintEntity", settings: "OsintSettings") -> "OsintScan":
    """Esegue tutti gli enricher sull'entità e salva il risultato in un nuovo OsintScan.

    Ritorna l'oggetto OsintScan creato (status completed o failed).
    """
    from apps.osint.models import OsintScan, ScanStatus
    from apps.osint.enrichers import ssl, dns, whois_enr, virustotal, abuseipdb, otx, gsb, hibp
    from apps.osint.scoring import compute_scores

    scan = OsintScan.objects.create(entity=entity, status=ScanStatus.RUNNING)

    results: list[bool] = []

    # SSL (crt.sh — throttle dopo)
    results.append(ssl.run(entity, scan, settings))
    time.sleep(DELAY_CRTSH_VT)

    # DNS — lookup locale, nessun throttle
    results.append(dns.run(entity, scan, settings))

    # WHOIS — locale
    results.append(whois_enr.run(entity, scan, settings))

    # VirusTotal (throttle dopo)
    results.append(virustotal.run(entity, scan, settings))
    time.sleep(DELAY_CRTSH_VT)

    # AbuseIPDB
    results.append(abuseipdb.run(entity, scan, settings))
    time.sleep(DELAY_ABUSE_OTX)

    # OTX
    results.append(otx.run(entity, scan, settings))
    time.sleep(DELAY_ABUSE_OTX)

    # Google Safe Browsing
    results.append(gsb.run(entity, scan, settings))
    time.sleep(DELAY_GSB)

    # HIBP (solo my_domain con api_key)
    results.append(hibp.run(entity, scan, settings))
    if settings.hibp_api_key:
        time.sleep(DELAY_HIBP)

    # Score
    compute_scores(entity, scan)

    # Status: failed solo se TUTTI i risultati critici (ssl+dns) falliscono
    scan.status = ScanStatus.FAILED if not any(results[:2]) else ScanStatus.COMPLETED
    scan.save()

    # Alert engine (solo se scan completato)
    if scan.status == ScanStatus.COMPLETED:
        from apps.osint.alerts import run_alerts
        alerts = run_alerts(entity, scan, settings)
        logger.info("Alert engine: %d alert creati per %s", len(alerts), entity.domain)

    logger.info(
        "Enrichment %s for %s — ssl=%s dns=%s vt=%s abu=%s otx=%s gsb=%s hibp=%s score=%d",
        scan.status, entity.domain,
        results[0], results[1], results[3], results[4], results[5], results[6], results[7],
        scan.score_total,
    )
    return scan

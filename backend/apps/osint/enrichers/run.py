"""Orchestratore enrichment OSINT.

Chiama tutti gli enricher in sequenza, rispetta rate limit globali via Redis
token bucket, salva OsintScan. Se almeno un enricher ha successo → 'completed'.
Se tutti falliscono → 'failed'.

Il throttle è centralizzato qui — non più sleep inline. Quando più scan girano
in parallelo (es. weekly scan via celery group), il bucket coordina i call rate.
Fallback: se Redis non risponde, si torna a `time.sleep` per non perdere il vincolo.
"""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from apps.osint.models import OsintEntity, OsintSettings

logger = logging.getLogger(__name__)

# Pausa minima tra chiamate per uno stesso bucket (sec).
DELAY_CRTSH_VT = 15      # crt.sh e VirusTotal: 4/min free
DELAY_ABUSE_OTX = 5      # AbuseIPDB e OTX: più generosi
DELAY_GSB = 2
DELAY_HIBP = 5

_THROTTLE_KEY_PREFIX = "osint:rate:"
_THROTTLE_MAX_WAIT = 60  # secondi: cap difensivo


def _acquire_token(bucket: str, min_interval: int) -> None:
    """Garantisce che tra due chiamate dello stesso bucket passino almeno
    `min_interval` secondi, anche tra worker Celery diversi.

    Usa Redis con `SET NX EX` come lock leggero: chi non riesce ad acquisire
    aspetta (al massimo `_THROTTLE_MAX_WAIT`) e poi tenta di nuovo.
    Se Redis non è raggiungibile, ricade su `time.sleep(min_interval)`.
    """
    try:
        from django.core.cache import cache
        key = f"{_THROTTLE_KEY_PREFIX}{bucket}"
        deadline = time.monotonic() + _THROTTLE_MAX_WAIT
        while True:
            if cache.add(key, "1", timeout=min_interval):
                return
            if time.monotonic() >= deadline:
                logger.warning("OSINT throttle %s: max wait reached, proceeding", bucket)
                return
            time.sleep(0.5)
    except Exception as exc:  # pragma: no cover - solo se Redis down
        logger.debug("Throttle Redis fallback (%s): %s", bucket, exc)
        time.sleep(min_interval)


def run_enrichment(entity: "OsintEntity", settings: "OsintSettings") -> "OsintScan":
    """Esegue tutti gli enricher sull'entità e salva il risultato in un nuovo OsintScan.

    Ritorna l'oggetto OsintScan creato (status completed o failed).
    """
    from apps.osint.models import OsintScan, ScanStatus
    from apps.osint.enrichers import (
        ssl, dns, whois_enr, virustotal, abuseipdb, otx, gsb, hibp,
        http_headers, dnsbl, dnstwist as dnstwist_enr, takeover,
    )
    from apps.osint.scoring import compute_scores

    scan = OsintScan.objects.create(entity=entity, status=ScanStatus.RUNNING)

    # Esiti per nome enricher: niente liste posizionali (riordinare gli enricher
    # non deve più poter falsare status/logging — vedi review).
    results: dict[str, bool] = {}

    # SSL (crt.sh): throttle PRIMA (non dopo) — così la prima chiamata può partire subito
    # ma ogni successivo scan dello stesso bucket attende.
    _acquire_token("crtsh", DELAY_CRTSH_VT)
    results["ssl"] = ssl.run(entity, scan, settings)

    # DNS — lookup locale, nessun throttle
    results["dns"] = dns.run(entity, scan, settings)

    # WHOIS — locale
    results["whois"] = whois_enr.run(entity, scan, settings)

    # VirusTotal
    if settings.virustotal_api_key:
        _acquire_token("virustotal", DELAY_CRTSH_VT)
    results["virustotal"] = virustotal.run(entity, scan, settings)

    # AbuseIPDB
    if settings.abuseipdb_api_key:
        _acquire_token("abuseipdb", DELAY_ABUSE_OTX)
    results["abuseipdb"] = abuseipdb.run(entity, scan, settings)

    # OTX
    _acquire_token("otx", DELAY_ABUSE_OTX)
    results["otx"] = otx.run(entity, scan, settings)

    # Google Safe Browsing
    if settings.gsb_api_key:
        _acquire_token("gsb", DELAY_GSB)
    results["gsb"] = gsb.run(entity, scan, settings)

    # DNSBL — reputazione via blocklist DNS (popola in_blacklist/blacklist_sources)
    _acquire_token("dnsbl", DELAY_GSB)
    results["dnsbl"] = dnsbl.run(entity, scan, settings)

    # HIBP (solo my_domain con api_key)
    if settings.hibp_api_key:
        _acquire_token("hibp", DELAY_HIBP)
    results["hibp"] = hibp.run(entity, scan, settings)

    # HTTP security headers — locale (HEAD/GET su https://{domain})
    results["http_headers"] = http_headers.run(entity, scan, settings)

    # Subdomain takeover — DNS-only sui sottodomini inclusi (popolati da ssl/crt.sh
    # sopra). Nessun throttle: solo lookup CNAME/A locali.
    results["takeover"] = takeover.run(entity, scan, settings)

    # dnstwist — opzionale (skip se libreria non installata). Pesante: solo my_domain.
    if entity.entity_type == "my_domain":
        results["dnstwist"] = dnstwist_enr.run(entity, scan, settings)

    # Score (passa settings per evitare un reload)
    compute_scores(entity, scan, settings)

    # Status: failed solo se ENTRAMBI gli enricher critici (ssl+dns) falliscono.
    scan.status = (
        ScanStatus.FAILED
        if not (results.get("ssl") or results.get("dns"))
        else ScanStatus.COMPLETED
    )
    scan.save()

    # Alert engine + Finding engine (solo se scan completato)
    if scan.status == ScanStatus.COMPLETED:
        from apps.osint.alerts import run_alerts
        alerts = run_alerts(entity, scan, settings)
        logger.info("Alert engine: %d alert creati per %s", len(alerts), entity.domain)

        from apps.osint.findings import sync_findings
        f_created, f_updated, f_resolved = sync_findings(entity, scan)
        logger.info(
            "Finding engine for %s: created=%d updated=%d auto_resolved=%d",
            entity.domain, f_created, f_updated, f_resolved,
        )

    logger.info(
        "Enrichment %s for %s — %s score=%d",
        scan.status, entity.domain,
        " ".join(f"{k}={'ok' if v else 'ko'}" for k, v in results.items()),
        scan.score_total,
    )
    return scan

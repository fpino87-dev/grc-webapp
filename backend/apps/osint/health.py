"""Salute degli enricher OSINT a chiave.

Una *probe* è una chiamata autenticata leggera (no scan, target neutro) che
verifica se la chiave di un provider è valida e interrogabile. L'esito è uno di:

- ``ok``           — autenticazione riuscita (la chiave funziona)
- ``invalid``      — chiave rifiutata (HTTP 401/403, o 400 per GSB): azione richiesta
- ``rate_limited`` — chiave valida ma quota esaurita ora (HTTP 429): non è un guasto
- ``error``        — errore di rete/HTTP imprevisto (transitorio)
- ``no_key``       — nessuna chiave configurata

Lo stato per provider viene salvato in ``OsintSettings.enricher_health`` (mai la
chiave: solo esito, timestamp e dettaglio troncato) e alimenta il semaforo nella
pagina impostazioni OSINT. Le probe riusano il client `requests` degli enricher
così la salute riflette esattamente ciò che gira nello scan reale.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

from django.utils import timezone

if TYPE_CHECKING:
    from apps.osint.models import OsintSettings

logger = logging.getLogger(__name__)

# Provider con chiave gestiti dal semaforo.
KEYED_PROVIDERS: tuple[str, ...] = ("virustotal", "abuseipdb", "gsb", "hibp", "abusech")


def classify_http(status_code: int, invalid_codes: tuple[int, ...] = (401, 403)) -> str:
    """Mappa un HTTP status in uno stato di salute.

    `invalid_codes` è parametrico perché GSB segnala la chiave non valida con 400.
    Un 404 conta come ``ok``: l'autenticazione è andata a buon fine, semplicemente
    la risorsa neutra non esiste (es. account/dominio non presente)."""
    if status_code in invalid_codes:
        return "invalid"
    if status_code == 429:
        return "rate_limited"
    if 200 <= status_code < 300 or status_code == 404:
        return "ok"
    return "error"


def _probes() -> dict[str, Callable[["OsintSettings"], tuple[str, str]]]:
    from apps.osint.enrichers import virustotal, abuseipdb, gsb, hibp, abusech
    return {
        "virustotal": virustotal.probe,
        "abuseipdb": abuseipdb.probe,
        "gsb": gsb.probe,
        "hibp": hibp.probe,
        "abusech": abusech.probe,
    }


def check_enricher_health(
    settings: "OsintSettings | None" = None,
    providers: "list[str] | None" = None,
    save: bool = True,
) -> dict:
    """Esegue le probe dei provider richiesti e (di default) salva l'esito.

    Ritorna il dict ``{provider: {status, detail, checked_at}}`` aggiornato.
    `providers=None` → tutti i provider keyed. Aggiorna solo i provider testati,
    preservando gli esiti precedenti degli altri.
    """
    from apps.osint.models import OsintSettings

    if settings is None:
        settings = OsintSettings.load()

    targets = [p for p in (providers or KEYED_PROVIDERS) if p in KEYED_PROVIDERS]
    probes = _probes()
    now = timezone.now().isoformat()

    health = dict(settings.enricher_health or {})
    for provider in targets:
        try:
            status, detail = probes[provider](settings)
        except Exception as exc:  # noqa: BLE001 - una probe non deve mai propagare
            logger.warning("OSINT probe %s crashed: %s", provider, exc)
            status, detail = "error", str(exc)[:200]
        health[provider] = {"status": status, "detail": detail, "checked_at": now}
        logger.info("OSINT enricher health %s → %s (%s)", provider, status, detail)

    if save:
        settings.enricher_health = health
        settings.save(update_fields=["enricher_health", "updated_at"])

    return health

"""abuse.ch Enricher — opzionale, threat intelligence CTI.

Interroga due feed gratuiti di abuse.ch (stessa Auth-Key):

- **ThreatFox** (`threatfox-api.abuse.ch`): database di Indicatori di Compromissione
  (IoC) associati a malware/botnet attivi. Cerca il dominio e il suo IP pubblico
  risolto → un match significa che l'entità è (o è stata di recente) coinvolta in
  infrastruttura malevola nota.
- **URLhaus** (`urlhaus-api.abuse.ch`): URL che distribuiscono malware. Interroga
  l'host → un match significa che il dominio ospita/ha ospitato payload malevoli.

Pattern keyed: senza `OsintSettings.abusech_api_key` l'enricher è un no-op
(`return True`), come gli altri enricher a chiave (virustotal/abuseipdb/gsb).
La Auth-Key abuse.ch è gratuita (registrazione su auth.abuse.ch).
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from apps.osint.models import OsintEntity, OsintScan, OsintSettings

logger = logging.getLogger(__name__)

THREATFOX_URL = "https://threatfox-api.abuse.ch/api/v1/"
URLHAUS_HOST_URL = "https://urlhaus-api.abuse.ch/v1/host/"
TIMEOUT = 15
# Cap difensivi su ciò che salviamo nello scan.
MAX_MALWARE = 20


def _threatfox_search(term: str, api_key: str) -> list[dict]:
    """Cerca un IoC (dominio o IP) su ThreatFox. Ritorna la lista di IoC match.

    Non solleva: in caso di errore di rete/HTTP/parse ritorna lista vuota (il
    chiamante traccia l'errore in enricher_errors). `no_result` → lista vuota.
    """
    resp = requests.post(
        THREATFOX_URL,
        json={"query": "search_ioc", "search_term": term},
        headers={"Auth-Key": api_key, "Accept": "application/json"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("query_status") != "ok":
        return []  # no_result / illegal_search_term / ...
    data = body.get("data")
    return data if isinstance(data, list) else []


def _urlhaus_host(host: str, api_key: str) -> int:
    """Conta gli URL malevoli noti a URLhaus per l'host. -1 = errore/non disponibile."""
    resp = requests.post(
        URLHAUS_HOST_URL,
        data={"host": host},
        headers={"Auth-Key": api_key, "Accept": "application/json"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    body = resp.json()
    status = body.get("query_status")
    if status == "no_results":
        return 0
    if status != "ok":
        return -1
    urls = body.get("urls")
    if isinstance(urls, list):
        return len(urls)
    try:
        return int(body.get("url_count") or 0)
    except (TypeError, ValueError):
        return 0


def run(entity: "OsintEntity", scan: "OsintScan", settings: "OsintSettings") -> bool:
    from apps.osint.validators import assert_public_or_log, safe_resolve_public_ip

    api_key = settings.abusech_api_key
    if not api_key:
        return True  # saltato silenziosamente (no-op senza chiave)

    domain = entity.domain
    if not assert_public_or_log(domain, "abusech"):
        scan.enricher_errors["abusech"] = "non_public_target"
        return False

    ok_any = False

    # --- ThreatFox: dominio + IP pubblico risolto (dedup per id IoC) ---
    try:
        terms = [domain]
        ip = safe_resolve_public_ip(domain)
        if ip:
            terms.append(ip)

        iocs: dict = {}
        malware: list[str] = []
        seen_malware: set[str] = set()
        for term in terms:
            for ioc in _threatfox_search(term, api_key):
                key = ioc.get("id") or ioc.get("ioc")
                if key in iocs:
                    continue
                iocs[key] = ioc
                label = (ioc.get("malware_printable") or ioc.get("malware") or "").strip()
                if label and label.lower() not in seen_malware:
                    seen_malware.add(label.lower())
                    malware.append(label)

        scan.threatfox_iocs = len(iocs)
        scan.threatfox_malware = malware[:MAX_MALWARE]
        ok_any = True
    except Exception as exc:
        logger.warning("ThreatFox enricher failed for %s: %s", domain, exc)
        scan.enricher_errors["threatfox"] = str(exc)

    # --- URLhaus: URL malevoli per l'host ---
    try:
        count = _urlhaus_host(domain, api_key)
        if count >= 0:
            scan.urlhaus_urls = count
            ok_any = True
        else:
            scan.enricher_errors["urlhaus"] = "unexpected_status"
    except Exception as exc:
        logger.warning("URLhaus enricher failed for %s: %s", domain, exc)
        scan.enricher_errors["urlhaus"] = str(exc)

    return ok_any


def probe(settings: "OsintSettings") -> tuple[str, str]:
    """Health-check leggero della Auth-Key abuse.ch (search_ioc su termine neutro).

    Con HTTP 200 la chiave è valida qualunque sia `query_status` (ok/no_result/
    illegal_search_term significano tutti "autenticato"). Chiave assente/errata →
    HTTP 401."""
    from apps.osint.health import classify_http

    if not settings.abusech_api_key:
        return ("no_key", "")
    try:
        resp = requests.post(
            THREATFOX_URL,
            json={"query": "search_ioc", "search_term": "example.com"},
            headers={"Auth-Key": settings.abusech_api_key, "Accept": "application/json"},
            timeout=TIMEOUT,
        )
        return (classify_http(resp.status_code), f"HTTP {resp.status_code}")
    except Exception as exc:  # noqa: BLE001
        return ("error", str(exc)[:200])

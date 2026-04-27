"""WHOIS Enricher — RDAP-first con fallback python-whois.

RDAP (RFC 7483) è il successore strutturato di WHOIS, espone JSON e ha rate limit
gestiti dai registry. Quando disponibile va preferito al WHOIS testuale.

Strategia:
1. Bootstrap IANA per individuare il server RDAP responsabile della TLD del dominio
2. GET {server}/domain/{domain} → estrai expiry / registrar / country / privacy
3. Se RDAP fallisce per qualsiasi motivo, fallback su `python-whois`

Tollerante a:
- libreria `python-whois` mancante (lascia campi vuoti, non errore fatale)
- TLD senza RDAP server pubblico (es. alcune ccTLD): salta direttamente al fallback
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from functools import lru_cache
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from apps.osint.models import OsintEntity, OsintScan, OsintSettings

logger = logging.getLogger(__name__)

PRIVACY_KEYWORDS = [
    "domains by proxy", "whoisguard", "privacy service", "redacted for privacy",
    "contact privacy", "privacyprotect", "perfect privacy", "data protected",
    "identity protection", "registrant privacy",
]

RDAP_BOOTSTRAP_URL = "https://data.iana.org/rdap/dns.json"
RDAP_TIMEOUT = 10


def _is_privacy(text: str) -> bool:
    low = (text or "").lower()
    return any(kw in low for kw in PRIVACY_KEYWORDS)


def _to_date(val) -> date | None:
    if val is None:
        return None
    if isinstance(val, list):
        val = val[0] if val else None
        if val is None:
            return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00")).date()
        except ValueError:
            return None
    return None


@lru_cache(maxsize=1)
def _rdap_bootstrap() -> dict[str, str]:
    """Mappa TLD → URL RDAP, da IANA bootstrap. Cached per processo."""
    try:
        resp = requests.get(RDAP_BOOTSTRAP_URL, timeout=RDAP_TIMEOUT)
        if resp.status_code != 200:
            return {}
        data = resp.json()
    except Exception as exc:
        logger.debug("RDAP bootstrap fetch failed: %s", exc)
        return {}

    mapping: dict[str, str] = {}
    for entry in data.get("services", []):
        if not isinstance(entry, list) or len(entry) < 2:
            continue
        tlds, urls = entry[0], entry[1]
        if not urls:
            continue
        # Prendi il primo URL HTTPS disponibile.
        url = next((u for u in urls if u.startswith("https://")), urls[0])
        url = url.rstrip("/")
        for tld in tlds:
            mapping[tld.lower()] = url
    return mapping


def _query_rdap(domain: str) -> dict | None:
    """Lookup RDAP per il dominio. None se non disponibile/fallisce."""
    parts = domain.lower().rsplit(".", 1)
    if len(parts) != 2:
        return None
    tld = parts[1]
    base = _rdap_bootstrap().get(tld)
    if not base:
        return None
    try:
        resp = requests.get(
            f"{base}/domain/{domain}",
            timeout=RDAP_TIMEOUT,
            headers={"Accept": "application/rdap+json"},
        )
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception as exc:
        logger.debug("RDAP query failed for %s: %s", domain, exc)
        return None


def _rdap_extract(data: dict) -> dict:
    """Estrae i campi WHOIS-equivalenti da una risposta RDAP."""
    out: dict = {
        "expiry": None,
        "registrar": "",
        "country": "",
        "privacy": False,
    }

    # Expiry: cerca evento di tipo "expiration".
    for ev in data.get("events", []) or []:
        if ev.get("eventAction") == "expiration":
            out["expiry"] = _to_date(ev.get("eventDate"))
            break

    # Registrar + country: nelle entity con role "registrar".
    for ent in data.get("entities", []) or []:
        roles = ent.get("roles", []) or []
        if "registrar" in roles:
            # vCard array: ["vcard", [["fn", {}, "text", "RegistrarName"], ...]]
            vcard = ent.get("vcardArray") or []
            if isinstance(vcard, list) and len(vcard) >= 2:
                for prop in vcard[1] or []:
                    if not isinstance(prop, list) or len(prop) < 4:
                        continue
                    key = prop[0]
                    val = prop[3]
                    if key == "fn" and isinstance(val, str):
                        out["registrar"] = val[:255]
                    if key == "adr" and isinstance(val, list):
                        # Country è l'ultimo elemento dell'address array
                        if val and isinstance(val[-1], str):
                            out["country"] = val[-1][:10]
            break

    # Privacy: cerca redaction nei testi (RDAP redaction extension RFC 9537).
    raw = str(data)
    if _is_privacy(raw) or _is_privacy(out["registrar"]):
        out["privacy"] = True
    return out


def _python_whois_fill(domain: str, scan: "OsintScan") -> bool:
    """Fallback su python-whois se RDAP non disponibile."""
    try:
        import whois
    except ImportError:
        scan.enricher_errors["whois"] = "python-whois not installed"
        return False
    try:
        data = whois.whois(domain)
        scan.domain_expiry_date = _to_date(data.expiration_date)
        scan.domain_registrar = (data.registrar or "")[:255]
        scan.registrar_country = (data.country or "")[:10] if hasattr(data, "country") else ""

        registrant = ""
        if hasattr(data, "registrant"):
            registrant = str(data.registrant or "")
        elif hasattr(data, "registrant_name"):
            registrant = str(data.registrant_name or "")
        scan.whois_privacy = _is_privacy(registrant) or _is_privacy(scan.domain_registrar)
        return True
    except Exception as exc:
        logger.debug("python-whois failed for %s: %s", domain, exc)
        scan.enricher_errors["whois"] = str(exc)
        return False


def run(entity: "OsintEntity", scan: "OsintScan", settings: "OsintSettings") -> bool:
    from apps.osint.validators import assert_public_or_log

    domain = entity.domain
    if not assert_public_or_log(domain, "whois"):
        scan.enricher_errors["whois"] = "non_public_target"
        return False

    rdap = _query_rdap(domain)
    if rdap is not None:
        fields = _rdap_extract(rdap)
        scan.domain_expiry_date = fields["expiry"]
        scan.domain_registrar = fields["registrar"]
        scan.registrar_country = fields["country"]
        scan.whois_privacy = fields["privacy"]
        return True

    # Fallback
    return _python_whois_fill(domain, scan)

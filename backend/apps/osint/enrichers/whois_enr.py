"""WHOIS Enricher — python-whois.

Raccoglie data scadenza dominio, registrar, privacy shield, paese registrar.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.osint.models import OsintEntity, OsintScan, OsintSettings

logger = logging.getLogger(__name__)

PRIVACY_KEYWORDS = [
    "domains by proxy", "whoisguard", "privacy service", "redacted for privacy",
    "contact privacy", "privacyprotect", "perfect privacy", "data protected",
    "identity protection", "registrant privacy",
]


def _is_privacy(registrant: str) -> bool:
    low = registrant.lower()
    return any(kw in low for kw in PRIVACY_KEYWORDS)


def _to_date(val) -> date | None:
    if val is None:
        return None
    if isinstance(val, list):
        val = val[0]
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    return None


def run(entity: "OsintEntity", scan: "OsintScan", settings: "OsintSettings") -> bool:
    domain = entity.domain
    try:
        import whois
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
        logger.debug("WHOIS enricher failed for %s: %s", domain, exc)
        scan.enricher_errors["whois"] = str(exc)
        return False

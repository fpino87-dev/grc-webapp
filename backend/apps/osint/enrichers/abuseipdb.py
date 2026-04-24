"""AbuseIPDB Enricher — opzionale, solo per entità con IP.

Risolve il dominio in IP se necessario, poi interroga AbuseIPDB.
"""
from __future__ import annotations

import logging
import socket
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from apps.osint.models import OsintEntity, OsintScan, OsintSettings

logger = logging.getLogger(__name__)

ABUSEIPDB_URL = "https://api.abuseipdb.com/api/v2/check"
TIMEOUT = 10


def _resolve_ip(domain: str) -> str | None:
    try:
        return socket.gethostbyname(domain)
    except Exception:
        return None


def run(entity: "OsintEntity", scan: "OsintScan", settings: "OsintSettings") -> bool:
    api_key = settings.abuseipdb_api_key
    if not api_key:
        return True  # saltato silenziosamente

    domain = entity.domain
    try:
        ip = _resolve_ip(domain)
        if not ip:
            return True  # non risolvibile → skip

        resp = requests.get(
            ABUSEIPDB_URL,
            params={"ipAddress": ip, "maxAgeInDays": 90},
            headers={"Key": api_key, "Accept": "application/json"},
            timeout=TIMEOUT,
        )
        if resp.status_code == 429:
            logger.warning("AbuseIPDB rate limit for %s", domain)
            scan.enricher_errors["abuseipdb"] = "rate_limit"
            return False
        resp.raise_for_status()

        data = resp.json().get("data", {})
        scan.abuseipdb_score = data.get("abuseConfidenceScore", 0)
        scan.abuseipdb_reports = data.get("totalReports", 0)
        return True
    except Exception as exc:
        logger.warning("AbuseIPDB enricher failed for %s: %s", domain, exc)
        scan.enricher_errors["abuseipdb"] = str(exc)
        return False

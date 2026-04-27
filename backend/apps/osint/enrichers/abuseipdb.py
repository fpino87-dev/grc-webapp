"""AbuseIPDB Enricher — opzionale, solo per entità con IP.

Risolve il dominio in IP se necessario, poi interroga AbuseIPDB.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from apps.osint.models import OsintEntity, OsintScan, OsintSettings

logger = logging.getLogger(__name__)

ABUSEIPDB_URL = "https://api.abuseipdb.com/api/v2/check"
TIMEOUT = 10


def run(entity: "OsintEntity", scan: "OsintScan", settings: "OsintSettings") -> bool:
    from apps.osint.validators import assert_public_or_log, safe_resolve_public_ip

    api_key = settings.abuseipdb_api_key
    if not api_key:
        return True  # saltato silenziosamente

    domain = entity.domain
    if not assert_public_or_log(domain, "abuseipdb"):
        scan.enricher_errors["abuseipdb"] = "non_public_target"
        return False
    try:
        ip = safe_resolve_public_ip(domain)
        if not ip:
            return True  # non risolvibile a IP pubblico → skip

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

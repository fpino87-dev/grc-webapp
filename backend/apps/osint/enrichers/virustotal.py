"""VirusTotal Enricher — API v3 (opzionale, solo con api_key configurata).

Free tier: 4 req/min, 500 req/day. Throttling gestito dall'orchestratore.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from apps.osint.models import OsintEntity, OsintScan, OsintSettings

logger = logging.getLogger(__name__)

VT_URL = "https://www.virustotal.com/api/v3/domains/{domain}"
VT_TIMEOUT = 15


def run(entity: "OsintEntity", scan: "OsintScan", settings: "OsintSettings") -> bool:
    from apps.osint.validators import assert_public_or_log

    api_key = settings.virustotal_api_key
    if not api_key:
        return True  # saltato silenziosamente

    domain = entity.domain
    if not assert_public_or_log(domain, "virustotal"):
        scan.enricher_errors["virustotal"] = "non_public_target"
        return False
    try:
        resp = requests.get(
            VT_URL.format(domain=domain),
            headers={"x-apikey": api_key},
            timeout=VT_TIMEOUT,
        )
        if resp.status_code == 404:
            scan.vt_malicious = 0
            scan.vt_suspicious = 0
            return True
        if resp.status_code == 429:
            logger.warning("VirusTotal rate limit hit for %s", domain)
            scan.enricher_errors["virustotal"] = "rate_limit"
            return False
        resp.raise_for_status()

        stats = resp.json().get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
        scan.vt_malicious = stats.get("malicious", 0)
        scan.vt_suspicious = stats.get("suspicious", 0)
        return True
    except Exception as exc:
        logger.warning("VirusTotal enricher failed for %s: %s", domain, exc)
        scan.enricher_errors["virustotal"] = str(exc)
        return False

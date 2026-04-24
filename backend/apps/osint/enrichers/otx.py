"""AlienVault OTX Enricher — gratuito senza API key.

Conta i pulse attivi per il dominio (> 0 = presenza in threat intelligence).
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from apps.osint.models import OsintEntity, OsintScan, OsintSettings

logger = logging.getLogger(__name__)

OTX_URL = "https://otx.alienvault.com/api/v1/indicators/domain/{domain}/general"
TIMEOUT = 15


def run(entity: "OsintEntity", scan: "OsintScan", settings: "OsintSettings") -> bool:
    domain = entity.domain
    try:
        headers = {}
        if settings.otx_api_key:
            headers["X-OTX-API-KEY"] = settings.otx_api_key

        resp = requests.get(
            OTX_URL.format(domain=domain),
            headers=headers,
            timeout=TIMEOUT,
        )
        if resp.status_code == 429:
            logger.warning("OTX rate limit for %s", domain)
            scan.enricher_errors["otx"] = "rate_limit"
            return False
        if resp.status_code == 404:
            scan.otx_pulses = 0
            return True
        resp.raise_for_status()

        scan.otx_pulses = resp.json().get("pulse_info", {}).get("count", 0)
        return True
    except Exception as exc:
        logger.warning("OTX enricher failed for %s: %s", domain, exc)
        scan.enricher_errors["otx"] = str(exc)
        return False

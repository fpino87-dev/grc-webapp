"""HIBP Enricher — Have I Been Pwned (solo entity_type = 'my_domain').

Richiede hibp_api_key in OsintSettings. MAI usare per domini fornitori.
Il dominio deve essere verificato su HIBP prima che l'API risponda.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from apps.osint.models import OsintEntity, OsintScan, OsintSettings

logger = logging.getLogger(__name__)

HIBP_URL = "https://haveibeenpwned.com/api/v3/breacheddomain/{domain}"
TIMEOUT = 15


def run(entity: "OsintEntity", scan: "OsintScan", settings: "OsintSettings") -> bool:
    from apps.osint.models import EntityType
    from apps.osint.validators import assert_public_or_log

    if entity.entity_type != EntityType.MY_DOMAIN:
        return True  # MAI per fornitori

    api_key = settings.hibp_api_key
    if not api_key:
        return True  # saltato silenziosamente

    domain = entity.domain
    if not assert_public_or_log(domain, "hibp"):
        scan.enricher_errors["hibp"] = "non_public_target"
        return False
    try:
        resp = requests.get(
            HIBP_URL.format(domain=domain),
            headers={
                "hibp-api-key": api_key,
                "User-Agent": "GRC-Webapp-OSINT/1.0",
            },
            timeout=TIMEOUT,
        )
        if resp.status_code == 404:
            scan.hibp_breaches = 0
            return True
        if resp.status_code == 401:
            logger.warning("HIBP invalid API key for %s", domain)
            scan.enricher_errors["hibp"] = "invalid_api_key"
            return False
        if resp.status_code == 429:
            scan.enricher_errors["hibp"] = "rate_limit"
            return False
        resp.raise_for_status()

        data = resp.json()  # {email: [breach_name, ...], ...}
        if not isinstance(data, dict):
            scan.hibp_breaches = 0
            return True

        scan.hibp_breaches = len(data)

        # Breach più recente e data types aggregati
        # HIBP breacheddomain non include date — contiamo solo il numero.
        # La data richiederebbe una seconda chiamata /breach/{name} non necessaria.
        all_types: set[str] = set()
        for breach_list in data.values():
            if isinstance(breach_list, list):
                all_types.update(breach_list)
        scan.hibp_data_types = sorted(all_types)
        return True
    except Exception as exc:
        logger.warning("HIBP enricher failed for %s: %s", domain, exc)
        scan.enricher_errors["hibp"] = str(exc)
        return False

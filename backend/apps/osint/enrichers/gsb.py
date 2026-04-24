"""Google Safe Browsing Enricher — API v4.

Richiede GSB_API_KEY in OsintSettings.gsb_api_key.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from apps.osint.models import OsintEntity, OsintScan, OsintSettings

logger = logging.getLogger(__name__)

GSB_URL = "https://safebrowsing.googleapis.com/v4/threatMatches:find"
TIMEOUT = 10
THREAT_TYPES = ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"]


def run(entity: "OsintEntity", scan: "OsintScan", settings: "OsintSettings") -> bool:
    api_key = settings.gsb_api_key
    if not api_key:
        return True  # saltato silenziosamente

    domain = entity.domain
    url = f"https://{domain}"
    try:
        payload = {
            "client": {"clientId": "grc-webapp-osint", "clientVersion": "1.0"},
            "threatInfo": {
                "threatTypes": THREAT_TYPES,
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": url}],
            },
        }
        resp = requests.post(
            GSB_URL,
            params={"key": api_key},
            json=payload,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        matches = data.get("matches", [])
        if not matches:
            scan.gsb_status = "safe"
        else:
            # Prende il tipo di minaccia più grave trovata
            threat_types = [m.get("threatType", "UNKNOWN") for m in matches]
            # Ordine di gravità
            priority = ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"]
            for t in priority:
                if t in threat_types:
                    scan.gsb_status = t.lower()
                    break
            else:
                scan.gsb_status = threat_types[0].lower()
        return True
    except Exception as exc:
        logger.warning("GSB enricher failed for %s: %s", domain, exc)
        scan.enricher_errors["gsb"] = str(exc)
        return False

"""HTTP Security Headers Enricher.

Verifica la presenza dei principali header HTTP di sicurezza:
- Strict-Transport-Security (HSTS)
- Content-Security-Policy (CSP)
- X-Frame-Options (XFO)
- X-Content-Type-Options (XCTO)
- Referrer-Policy
- Permissions-Policy

Salva il dettaglio in `OsintScan.security_headers`. Il finding `headers_missing`
viene poi generato da `findings.py` se almeno un header è mancante.

Tollerante: se HTTPS non è raggiungibile (no certificato, sito offline, IP-only)
salta silenziosamente senza fallire lo scan.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from apps.osint.models import OsintEntity, OsintScan, OsintSettings

logger = logging.getLogger(__name__)

HEADERS_TIMEOUT = 10
USER_AGENT = "GRC-OSINT-Scanner/1.0 (+passive security check)"

# Mapping (key interna → lista di header HTTP equivalenti).
HEADER_MAP: dict[str, tuple[str, ...]] = {
    "hsts": ("strict-transport-security",),
    "csp": ("content-security-policy", "content-security-policy-report-only"),
    "xfo": ("x-frame-options",),
    "xcto": ("x-content-type-options",),
    "referrer_policy": ("referrer-policy",),
    "permissions_policy": ("permissions-policy", "feature-policy"),
}


def _fetch_headers(domain: str) -> dict[str, str] | None:
    """HEAD su https://{domain}/ con fallback a GET. Headers lowercase. None se irraggiungibile."""
    for method in ("HEAD", "GET"):
        for host in (domain, f"www.{domain}"):
            url = f"https://{host}/"
            try:
                resp = requests.request(
                    method,
                    url,
                    timeout=HEADERS_TIMEOUT,
                    allow_redirects=True,
                    headers={"User-Agent": USER_AGENT},
                    stream=True,
                )
                # Anche 4xx/5xx con headers di sicurezza sono interessanti.
                if resp.status_code < 500:
                    headers = {k.lower(): v for k, v in resp.headers.items()}
                    resp.close()
                    return headers
            except Exception as exc:
                logger.debug("HTTP headers fetch %s %s failed: %s", method, url, exc)
                continue
    return None


def _evaluate(headers: dict[str, str]) -> dict:
    """Ritorna {chiave: bool, raw: {...}, missing: [chiavi mancanti]}."""
    out: dict = {}
    raw: dict = {}
    missing: list[str] = []
    for key, candidates in HEADER_MAP.items():
        present = False
        for h in candidates:
            if h in headers:
                present = True
                raw[h] = headers[h][:300]
                break
        out[key] = present
        if not present:
            missing.append(key)
    out["raw"] = raw
    out["missing"] = missing
    return out


def run(entity: "OsintEntity", scan: "OsintScan", settings: "OsintSettings") -> bool:
    from apps.osint.validators import assert_public_or_log

    domain = entity.domain
    if not assert_public_or_log(domain, "http_headers"):
        scan.enricher_errors["http_headers"] = "non_public_target"
        return False

    headers = _fetch_headers(domain)
    if headers is None:
        # Non raggiungibile via HTTPS: non è un errore in sé per OSINT passivo.
        # Lasciamo security_headers vuoto, il finding non scatterà.
        scan.security_headers = {}
        return True

    scan.security_headers = _evaluate(headers)
    return True

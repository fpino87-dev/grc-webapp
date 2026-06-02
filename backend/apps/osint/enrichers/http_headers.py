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
from urllib.parse import urljoin, urlparse

import requests

if TYPE_CHECKING:
    from apps.osint.models import OsintEntity, OsintScan, OsintSettings

logger = logging.getLogger(__name__)

HEADERS_TIMEOUT = 10
USER_AGENT = "GRC-OSINT-Scanner/1.0 (+passive security check)"
MAX_REDIRECTS = 4

# Mapping (key interna → lista di header HTTP equivalenti).
HEADER_MAP: dict[str, tuple[str, ...]] = {
    "hsts": ("strict-transport-security",),
    "csp": ("content-security-policy", "content-security-policy-report-only"),
    "xfo": ("x-frame-options",),
    "xcto": ("x-content-type-options",),
    "referrer_policy": ("referrer-policy",),
    "permissions_policy": ("permissions-policy", "feature-policy"),
}


def _request_no_redirect(method: str, url: str):
    """Singola richiesta senza seguire i redirect. None su errore."""
    try:
        return requests.request(
            method,
            url,
            timeout=HEADERS_TIMEOUT,
            allow_redirects=False,  # anti-SSRF: i redirect li seguiamo noi, validati
            headers={"User-Agent": USER_AGENT},
            stream=True,
        )
    except Exception as exc:
        logger.debug("HTTP headers fetch %s %s failed: %s", method, url, exc)
        return None


def _follow_validated(method: str, url: str) -> dict[str, str] | None:
    """Segue manualmente i redirect, rivalidando ad ogni hop che l'host di
    destinazione sia un target internet pubblico (anti-SSRF, review #3).

    Un dominio legittimo ma compromesso/misconfigurato potrebbe fare
    `302 → http://169.254.169.254/…` o verso un host interno: con
    allow_redirects=True `requests` lo seguirebbe. Qui ogni Location viene
    validato con `is_public_internet_target` prima di essere seguito.
    """
    from apps.osint.validators import is_public_internet_target

    seen: set[str] = set()
    for _ in range(MAX_REDIRECTS + 1):
        resp = _request_no_redirect(method, url)
        if resp is None:
            return None
        if 300 <= resp.status_code < 400 and "location" in {k.lower() for k in resp.headers}:
            location = resp.headers.get("Location") or resp.headers.get("location") or ""
            resp.close()
            if not location:
                return None
            next_url = urljoin(url, location)
            host = (urlparse(next_url).hostname or "").lower()
            if next_url in seen or not host or not is_public_internet_target(host):
                logger.debug("HTTP headers: redirect to non-public/looping host blocked: %s", next_url)
                return None
            seen.add(next_url)
            url = next_url
            continue
        if resp.status_code < 500:
            headers = {k.lower(): v for k, v in resp.headers.items()}
            resp.close()
            return headers
        resp.close()
        return None
    logger.debug("HTTP headers: max redirects reached")
    return None


def _fetch_headers(domain: str) -> dict[str, str] | None:
    """HEAD su https://{domain}/ con fallback a GET, redirect seguiti e validati.
    Headers lowercase. None se irraggiungibile."""
    for method in ("HEAD", "GET"):
        for host in (domain, f"www.{domain}"):
            headers = _follow_validated(method, f"https://{host}/")
            if headers is not None:
                return headers
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

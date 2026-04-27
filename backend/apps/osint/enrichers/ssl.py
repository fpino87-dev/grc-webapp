"""SSL Enricher — crt.sh + connessione TLS diretta.

Raccoglie:
- Certificato attivo dal dominio (TLS diretto)
- Sottodomini unici dai log Certificate Transparency (crt.sh)
"""
from __future__ import annotations

import logging
import socket
import ssl
from datetime import date, datetime, timezone as tz
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from apps.osint.models import OsintEntity, OsintScan, OsintSettings

logger = logging.getLogger(__name__)

CRTSH_URL = "https://crt.sh/?q=%.{domain}&output=json"
CRTSH_TIMEOUT = 20
TLS_TIMEOUT = 10
# Cap difensivo sul numero di sottodomini importati da CT log per scan.
# Domini molto popolari (es. cdn, ad-network, brand globali) possono restituire
# decine di migliaia di entry; importarle tutte gonfia OsintSubdomain e
# rallenta dashboard / aggregator.
CRTSH_MAX_SUBDOMAINS = 1000


def _get_tls_cert(domain: str) -> dict | None:
    """Connessione TLS diretta per leggere il certificato in uso."""
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=TLS_TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                return cert
    except Exception as exc:
        logger.debug("TLS direct check failed for %s: %s", domain, exc)
        return None


def _parse_cert(cert: dict) -> tuple[bool, date | None, int | None, str, bool]:
    """Ritorna (ssl_valid, expiry_date, days_remaining, issuer, wildcard)."""
    try:
        not_after_str = cert.get("notAfter", "")
        expiry = datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=tz.utc)
        now = datetime.now(tz=tz.utc)
        days_remaining = (expiry.date() - now.date()).days
        ssl_valid = days_remaining > 0

        # Estrae issuer in modo robusto: ogni RDN può contenere 1+ attributi
        issuer = ""
        for rdn in cert.get("issuer", []):
            for attr_key, attr_val in rdn:
                if attr_key in ("organizationName", "O"):
                    issuer = attr_val
                    break
                if attr_key in ("commonName", "CN") and not issuer:
                    issuer = attr_val
            if issuer:
                break

        subject_alt = cert.get("subjectAltName", [])
        wildcard = any(v.startswith("*.") for _, v in subject_alt)

        return ssl_valid, expiry.date(), days_remaining, issuer, wildcard
    except Exception as exc:
        logger.debug("Error parsing TLS cert: %s", exc)
        return False, None, None, "", False


def _get_crtsh_subdomains(domain: str) -> set[str]:
    """Recupera sottodomini unici dai log CT via crt.sh."""
    try:
        resp = requests.get(
            CRTSH_URL.format(domain=domain),
            timeout=CRTSH_TIMEOUT,
            headers={"Accept": "application/json"},
        )
        if resp.status_code != 200:
            return set()
        entries = resp.json()
    except Exception as exc:
        logger.debug("crt.sh request failed for %s: %s", domain, exc)
        return set()

    subdomains: set[str] = set()
    for entry in entries:
        name_value = entry.get("name_value", "")
        for name in name_value.split("\n"):
            name = name.strip().lower()
            if not name or name.startswith("*."):
                continue
            if name.endswith(f".{domain}") or name == domain:
                subdomains.add(name)
                if len(subdomains) >= CRTSH_MAX_SUBDOMAINS:
                    logger.info(
                        "crt.sh CT log truncated for %s at %d entries (cap reached)",
                        domain, CRTSH_MAX_SUBDOMAINS,
                    )
                    return subdomains
    return subdomains


def run(entity: "OsintEntity", scan: "OsintScan", settings: "OsintSettings") -> bool:
    from apps.osint.validators import assert_public_or_log

    domain = entity.domain
    if not assert_public_or_log(domain, "ssl"):
        scan.enricher_errors["ssl"] = "non_public_target"
        return False
    try:
        cert = _get_tls_cert(domain)
        if cert is None and not domain.startswith("www."):
            cert = _get_tls_cert(f"www.{domain}")

        if cert:
            ssl_valid, expiry, days, issuer, wildcard = _parse_cert(cert)
            scan.ssl_valid = ssl_valid
            scan.ssl_expiry_date = expiry
            scan.ssl_days_remaining = days
            scan.ssl_issuer = issuer[:255]
            scan.ssl_wildcard = wildcard
        # else: nessun HTTPS su domain né www.domain → ssl_valid rimane None (non applicabile)

        subdomains = _get_crtsh_subdomains(domain)
        # Aggiorna OsintSubdomain — aggiungi solo nuovi
        if subdomains:
            _sync_subdomains(entity, subdomains, settings)

        return True
    except Exception as exc:
        logger.warning("SSL enricher failed for %s: %s", domain, exc)
        scan.enricher_errors["ssl"] = str(exc)
        return False


def _sync_subdomains(entity: "OsintEntity", found: set[str], settings: "OsintSettings") -> None:
    from django.utils import timezone

    from apps.osint.models import OsintSubdomain, SubdomainAutoInclude, SubdomainStatus

    auto = settings.subdomain_auto_include
    now = timezone.now()
    initial_status = (
        SubdomainStatus.INCLUDED if auto == SubdomainAutoInclude.YES else SubdomainStatus.PENDING
    )

    existing_qs = OsintSubdomain.objects.filter(
        entity=entity, subdomain__in=found, deleted_at__isnull=True,
    ).only("id", "subdomain", "last_seen")
    existing_map = {o.subdomain: o for o in existing_qs}

    new_objs = [
        OsintSubdomain(entity=entity, subdomain=sub, status=initial_status, last_seen=now)
        for sub in found if sub not in existing_map
    ]
    if new_objs:
        OsintSubdomain.objects.bulk_create(new_objs, ignore_conflicts=True, batch_size=500)

    if existing_map:
        to_touch = list(existing_map.values())
        for obj in to_touch:
            obj.last_seen = now
        OsintSubdomain.objects.bulk_update(to_touch, ["last_seen"], batch_size=500)

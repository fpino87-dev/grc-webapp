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
# Cap sulla dimensione della risposta crt.sh letta in memoria. Domini globali
# possono restituire risposte JSON da decine di MB: leggerle interamente prima
# di troncare i sottodomini è uno spreco di memoria (review #9).
CRTSH_MAX_BYTES = 8 * 1024 * 1024  # 8 MB
# Cap difensivo sul numero di sottodomini importati da CT log per scan.
# Domini molto popolari (es. cdn, ad-network, brand globali) possono restituire
# decine di migliaia di entry; importarle tutte gonfia OsintSubdomain e
# rallenta dashboard / aggregator.
CRTSH_MAX_SUBDOMAINS = 1000

# OID → nome compatibile con ssl.getpeercert() per la costruzione del dict issuer.
_OID_NAMES: dict[str, str] = {
    "2.5.4.3": "commonName",
    "2.5.4.6": "countryName",
    "2.5.4.10": "organizationName",
    "2.5.4.11": "organizationalUnitName",
}


def _der_to_ssl_dict(der: bytes) -> dict | None:
    """Converte DER grezzo in un dict compatibile con ssl.getpeercert().

    Usato quando la connessione TLS riesce in modalità no-verify (cert scaduto
    o self-signed) ma vogliamo comunque estrarre notAfter/issuer/SAN.
    """
    try:
        from cryptography import x509 as cx509
        cert = cx509.load_der_x509_certificate(der)

        not_after = cert.not_valid_after_utc.strftime("%b %d %H:%M:%S %Y GMT")

        issuer_rdns = tuple(
            (((_OID_NAMES.get(a.oid.dotted_string, a.oid.dotted_string), a.value),),)
            for a in cert.issuer
        )

        san: list[tuple[str, str]] = []
        try:
            ext = cert.extensions.get_extension_for_class(cx509.SubjectAlternativeName)
            san = [("DNS", n.value) for n in ext.value if isinstance(n, cx509.DNSName)]
        except Exception:
            pass

        return {"notAfter": not_after, "issuer": issuer_rdns, "subjectAltName": san}
    except Exception as exc:
        logger.debug("DER cert parse failed: %s", exc)
        return None


def _get_tls_cert(domain: str) -> dict | None:
    """Connessione TLS diretta per leggere il certificato in uso.

    Prima tenta con verifica completa del certificato. Se la verifica fallisce per
    un problema TLS (cert scaduto, self-signed, mismatch) riprova senza verifica
    in modo da rilevare comunque i dati del certificato (scadenza, emittente).
    Ritorna None solo se il server HTTPS non è raggiungibile.

    Anti-SSRF / anti DNS-rebinding (review #3): il dominio viene risolto a un IP
    PUBBLICO validato e la connessione TCP avviene verso quell'IP (pinning),
    mentre SNI e hostname-check restano sul dominio. Così tra validazione e
    connessione non c'è una seconda risoluzione che un attaccante possa dirottare
    verso un IP privato/metadata.
    """
    from apps.osint.validators import safe_resolve_public_ip

    ip = safe_resolve_public_ip(domain)
    if not ip:
        return None  # non risolvibile a un IP pubblico → non connettere

    # Tentativo 1: verifica completa (connessione all'IP pinnato, SNI=domain)
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((ip, 443), timeout=TLS_TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                return ssock.getpeercert()
    except ssl.SSLError:
        pass  # problema certificato — riprova senza verifica
    except Exception as exc:
        logger.debug("TLS direct check failed for %s (%s): %s", domain, ip, exc)
        return None  # server non raggiungibile

    # Tentativo 2: no-verify per rilevare cert scaduti/non validi
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((ip, 443), timeout=TLS_TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                der = ssock.getpeercert(binary_form=True)
        if not der:
            return None
        return _der_to_ssl_dict(der)
    except Exception as exc:
        logger.debug("TLS no-verify check failed for %s (%s): %s", domain, ip, exc)
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


def _fetch_crtsh_entries(domain: str) -> list[dict]:
    """Scarica le entry JSON dei log CT via crt.sh (una sola chiamata di rete).

    Usata sia per l'enumerazione sottodomini sia per il CT monitoring (enrichers/ct.py),
    così non si interroga crt.sh due volte. Ritorna [] su errore o risposta troppo grande."""
    try:
        import json as _json

        resp = requests.get(
            CRTSH_URL.format(domain=domain),
            timeout=CRTSH_TIMEOUT,
            headers={"Accept": "application/json"},
            stream=True,
        )
        if resp.status_code != 200:
            resp.close()
            return []
        # Legge al massimo CRTSH_MAX_BYTES per evitare di caricare in RAM
        # risposte enormi; se eccede, scarta (non affidabile/parziale).
        raw = resp.raw.read(CRTSH_MAX_BYTES + 1, decode_content=True)
        resp.close()
        if len(raw) > CRTSH_MAX_BYTES:
            logger.warning("crt.sh response for %s exceeds %d bytes, skipping", domain, CRTSH_MAX_BYTES)
            return []
        return _json.loads(raw.decode("utf-8", errors="replace"))
    except Exception as exc:
        logger.debug("crt.sh request failed for %s: %s", domain, exc)
        return []


def _subdomains_from_entries(entries: list[dict], domain: str) -> set[str]:
    """Estrae sottodomini unici dalle entry crt.sh (con cap difensivo)."""
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

        entries = _fetch_crtsh_entries(domain)
        subdomains = _subdomains_from_entries(entries, domain)
        # Aggiorna OsintSubdomain — aggiungi solo nuovi
        if subdomains:
            _sync_subdomains(entity, subdomains, settings)

        # CT monitoring: analizza i certificati recenti dalle stesse entry crt.sh
        # (nessuna seconda chiamata di rete). Best-effort: non deve far fallire SSL.
        try:
            from apps.osint.enrichers import ct
            ct.analyze_ct(entity, scan, entries, settings)
        except Exception as exc:  # noqa: BLE001
            logger.warning("CT monitoring analysis failed for %s: %s", domain, exc)

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

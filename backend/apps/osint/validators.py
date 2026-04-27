"""Validatori di sicurezza per il modulo OSINT.

Tutti gli enricher chiamano host esterni a partire da input controllato dall'utente
(domini di Plant/Supplier/Asset). Senza filtri il backend potrebbe colpire risorse
private (RFC1918, link-local, cloud metadata, host del laboratorio interno).

Questa utility è la prima riga di difesa SSRF: rifiuta domini privati, locali,
loopback, multicast, riservati e hostname non risolvibili pubblicamente.
"""
from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Iterable

logger = logging.getLogger(__name__)

# Suffissi di dominio tipici di reti interne / servizi non instradabili.
_PRIVATE_SUFFIXES: tuple[str, ...] = (
    ".local",
    ".localhost",
    ".internal",
    ".lan",
    ".intranet",
    ".corp",
    ".home",
    ".test",
    ".example",
    ".invalid",
    ".onion",
)

_RESERVED_HOSTS: frozenset[str] = frozenset({
    "localhost",
    "ip6-localhost",
    "ip6-loopback",
    "broadcasthost",
})


def _ip_is_public(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    if ip.is_loopback or ip.is_link_local or ip.is_multicast:
        return False
    if ip.is_private or ip.is_reserved or ip.is_unspecified:
        return False
    # Bocca cloud metadata IPs noti (AWS/GCP/Azure 169.254.169.254 già coperto da link_local).
    return True


def _resolve_all(hostname: str) -> list[str]:
    """Ritorna tutti gli IP (A/AAAA) noti per l'hostname.

    Non solleva: in caso di errore ritorna lista vuota — il chiamante decide se
    bocciare o saltare l'enricher silenziosamente.
    """
    try:
        infos = socket.getaddrinfo(hostname, None)
    except OSError:
        return []
    ips: list[str] = []
    seen: set[str] = set()
    for fam, _, _, _, sockaddr in infos:
        if fam not in (socket.AF_INET, socket.AF_INET6):
            continue
        ip = sockaddr[0]
        # Per IPv6 strip eventuale zone id "%eth0".
        if "%" in ip:
            ip = ip.split("%", 1)[0]
        if ip not in seen:
            seen.add(ip)
            ips.append(ip)
    return ips


def is_public_internet_target(domain_or_ip: str) -> bool:
    """True se possiamo emettere richieste verso questo target da internet.

    - Rifiuta loopback / link-local / privati / multicast / reserved / unspecified.
    - Rifiuta hostname con TLD interni (.local, .internal, ecc.).
    - Per gli hostname risolve A/AAAA e accetta solo se TUTTI gli IP sono pubblici.
    """
    if not domain_or_ip:
        return False
    target = domain_or_ip.strip().lower().rstrip(".")
    if not target:
        return False

    # Rifiuta IP literal direttamente.
    try:
        ipaddress.ip_address(target)
        return _ip_is_public(target)
    except ValueError:
        pass  # è un hostname

    if target in _RESERVED_HOSTS:
        return False
    if any(target == s.lstrip(".") or target.endswith(s) for s in _PRIVATE_SUFFIXES):
        return False

    ips = _resolve_all(target)
    if not ips:
        # Non risolvibile: per sicurezza, rifiuta. Gli enricher passivi (crt.sh)
        # possono aggirare il check usando `is_safe_external_url` su singole URL.
        return False
    return all(_ip_is_public(ip) for ip in ips)


def safe_resolve_public_ip(hostname: str) -> str | None:
    """Risolve un hostname a un IP pubblico, oppure None se uno qualunque degli IP è privato.

    Pensato per AbuseIPDB e altri enricher che prendono in input un IP risolto.
    """
    ips = _resolve_all(hostname)
    if not ips:
        return None
    if not all(_ip_is_public(ip) for ip in ips):
        return None
    return ips[0]


def assert_public_or_log(domain: str, enricher_name: str) -> bool:
    """Wrapper che logga in DEBUG quando l'enricher salta un dominio non pubblico."""
    if is_public_internet_target(domain):
        return True
    logger.debug("OSINT enricher %s skipped: %s is not a public internet target", enricher_name, domain)
    return False

"""DNSBL Enricher — reputazione via blocklist DNS pubbliche.

Popola `scan.in_blacklist` e `scan.blacklist_sources`, segnali finora dichiarati
nel modello ma mai valorizzati. Usa lookup DNS (nessuna API key):

- IP-based  : zen.spamhaus.org, bl.spamcop.net  (l'IP risolto del dominio)
- domain-based: dbl.spamhaus.org                (il dominio stesso)

Una risposta A in 127.0.0.0/8 indica "listed". I codici 127.255.255.x sono
errori/limiti di query (es. uso da resolver pubblico) e vengono ignorati.

Nota operativa: le blocklist Spamhaus limitano l'uso da resolver pubblici
condivisi; in produzione il volume settimanale del modulo è ampiamente sotto
soglia. In caso di errore l'enricher è conservativo: non marca blacklist.
"""
from __future__ import annotations

import ipaddress
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.osint.models import OsintEntity, OsintScan, OsintSettings

logger = logging.getLogger(__name__)

DNSBL_TIMEOUT = 5

# Blocklist IP-based: il target è l'IP risolto (ottetti invertiti).
_IP_DNSBLS: dict[str, str] = {
    "zen.spamhaus.org": "Spamhaus ZEN",
    "bl.spamcop.net": "SpamCop",
}
# Blocklist domain-based: il target è il dominio.
_DOMAIN_DNSBLS: dict[str, str] = {
    "dbl.spamhaus.org": "Spamhaus DBL",
}


def _is_listed_response(ips: list[str]) -> bool:
    """True se almeno un IP è un 'hit' valido in 127.0.0.0/8 (esclusi i codici
    di errore 127.255.255.x usati da Spamhaus per segnalare query rifiutate)."""
    for ip in ips:
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if addr in ipaddress.ip_network("127.0.0.0/8"):
            if addr in ipaddress.ip_network("127.255.255.0/24"):
                continue  # codice di errore/limite, non un listing reale
            return True
    return False


def _query(name: str) -> list[str]:
    import dns.resolver
    try:
        resolver = dns.resolver.Resolver()
        resolver.lifetime = DNSBL_TIMEOUT
        resolver.timeout = DNSBL_TIMEOUT
        answers = resolver.resolve(name, "A", raise_on_no_answer=False)
        return [r.address for r in answers]
    except Exception:
        return []


def run(entity: "OsintEntity", scan: "OsintScan", settings: "OsintSettings") -> bool:
    from apps.osint.validators import assert_public_or_log, safe_resolve_public_ip

    domain = entity.domain
    if not assert_public_or_log(domain, "dnsbl"):
        scan.enricher_errors["dnsbl"] = "non_public_target"
        return False

    try:
        sources: list[str] = []

        # IP-based: richiede un IP pubblico risolto.
        ip = safe_resolve_public_ip(domain)
        if ip:
            try:
                reversed_ip = ".".join(reversed(ip.split(".")))  # solo IPv4
                if reversed_ip != ip or ":" not in ip:  # skip IPv6 (formato diverso)
                    for zone, label in _IP_DNSBLS.items():
                        if _is_listed_response(_query(f"{reversed_ip}.{zone}")):
                            sources.append(label)
            except Exception as exc:  # pragma: no cover
                logger.debug("DNSBL IP lookup failed for %s: %s", domain, exc)

        # Domain-based.
        for zone, label in _DOMAIN_DNSBLS.items():
            if _is_listed_response(_query(f"{domain}.{zone}")):
                sources.append(label)

        if sources:
            scan.in_blacklist = True
            scan.blacklist_sources = sorted(set(sources))
        else:
            scan.in_blacklist = False
            scan.blacklist_sources = []
        return True
    except Exception as exc:
        logger.warning("DNSBL enricher failed for %s: %s", domain, exc)
        scan.enricher_errors["dnsbl"] = str(exc)
        return False

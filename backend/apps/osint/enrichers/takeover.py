"""Subdomain takeover detection enricher.

Per i sottodomini inclusi (`status=included`) risolve la catena CNAME e la
confronta con i fingerprint di servizi cloud che, quando l'utente dismette la
risorsa (bucket S3, app Heroku, sito GitHub Pages, ...), lasciano il record
CNAME "dangling" e quindi rivendicabile da un attaccante → subdomain takeover.

Euristica DNS-only (nessuna richiesta HTTP → nessuna superficie SSRF):
1. Risolve il CNAME del sottodominio.
2. Se il target del CNAME corrisponde a un servizio noto (suffisso fingerprint).
3. E il target NON risolve (NXDOMAIN) → la risorsa è stata dismessa → candidato.

Limite noto: i servizi il cui endpoint risolve sempre (es. CloudFront/Fastly che
restituiscono comunque un IP edge) non vengono colti da questa euristica DNS-only;
servirebbe un fingerprint sul corpo HTTP. È un trade-off accettabile per evitare
richieste HTTP verso target controllati esternamente.

I candidati vengono salvati in `OsintScan.takeover_candidates` come lista di
`{"subdomain": str, "cname": str, "service": str}`. Il finding
`subdomain_takeover` (CRITICAL) viene generato da `findings.py` se la lista non
è vuota.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.osint.models import OsintEntity, OsintScan, OsintSettings

logger = logging.getLogger(__name__)

DNS_TIMEOUT = 5
# Cap difensivi: domini con molti sottodomini inclusi non devono trasformare lo
# scan in centinaia di lookup DNS.
MAX_SUBDOMAINS_CHECKED = 100
MAX_CANDIDATES = 20

# service → suffissi (substring) tipici del target CNAME quando il sottodominio
# è servito da quel provider. Volutamente specifici per limitare i falsi positivi.
_FINGERPRINTS: dict[str, tuple[str, ...]] = {
    "AWS S3": (".s3.amazonaws.com", ".s3-website", ".s3-website."),
    "AWS CloudFront": (".cloudfront.net",),
    "GitHub Pages": (".github.io",),
    "Heroku": (".herokuapp.com", ".herokudns.com"),
    "Azure": (
        ".azurewebsites.net", ".cloudapp.net", ".cloudapp.azure.com",
        ".trafficmanager.net", ".blob.core.windows.net", ".azureedge.net",
        ".azure-api.net",
    ),
    "Fastly": (".fastly.net",),
    "Shopify": (".myshopify.com",),
    "Pantheon": (".pantheonsite.io",),
    "Tumblr": (".domains.tumblr.com",),
    "Zendesk": (".zendesk.com",),
    "Surge.sh": (".surge.sh",),
    "Bitbucket": (".bitbucket.io",),
    "Ghost": (".ghost.io",),
    "Read the Docs": (".readthedocs.io",),
    "WordPress": (".wordpress.com",),
    "Netlify": (".netlify.app", ".netlify.com"),
    "Unbounce": (".unbouncepages.com",),
    "Helpscout": (".helpscoutdocs.com",),
    "Wix": (".wixdns.net",),
}


def _resolver():
    import dns.resolver
    r = dns.resolver.Resolver()
    r.lifetime = DNS_TIMEOUT
    r.timeout = DNS_TIMEOUT
    return r


def _cname_target(name: str) -> str | None:
    """Ritorna il target finale del CNAME (lowercase, senza trailing dot) o None."""
    import dns.resolver
    try:
        ans = _resolver().resolve(name, "CNAME", raise_on_no_answer=False)
        for r in ans:
            return str(r.target).rstrip(".").lower()
    except dns.resolver.NXDOMAIN:
        # Il sottodominio stesso non esiste: niente CNAME da valutare.
        return None
    except Exception:
        return None
    return None


def _target_resolves(name: str) -> bool | None:
    """True se il target risolve (A/AAAA), False se NXDOMAIN (dangling), None se incerto."""
    import dns.resolver
    try:
        a = _resolver().resolve(name, "A", raise_on_no_answer=False)
        if list(a):
            return True
        aaaa = _resolver().resolve(name, "AAAA", raise_on_no_answer=False)
        return bool(list(aaaa))
    except dns.resolver.NXDOMAIN:
        return False
    except Exception:
        return None


def _match_service(cname: str) -> str | None:
    for service, suffixes in _FINGERPRINTS.items():
        if any(s in cname for s in suffixes):
            return service
    return None


def run(entity: "OsintEntity", scan: "OsintScan", settings: "OsintSettings") -> bool:
    from apps.osint.models import OsintSubdomain, SubdomainStatus

    try:
        subdomains = list(
            OsintSubdomain.objects.filter(
                entity=entity,
                status=SubdomainStatus.INCLUDED,
                deleted_at__isnull=True,
            ).values_list("subdomain", flat=True)[:MAX_SUBDOMAINS_CHECKED]
        )

        candidates: list[dict] = []
        for sub in subdomains:
            cname = _cname_target(sub)
            if not cname:
                continue
            service = _match_service(cname)
            if not service:
                continue
            # Dangling solo se il target del CNAME è NXDOMAIN (risorsa dismessa).
            if _target_resolves(cname) is False:
                candidates.append({"subdomain": sub, "cname": cname, "service": service})
                logger.info(
                    "OSINT takeover candidate: %s → %s (%s) — target NXDOMAIN",
                    sub, cname, service,
                )
                if len(candidates) >= MAX_CANDIDATES:
                    break

        scan.takeover_candidates = candidates
        return True
    except Exception as exc:
        logger.warning("Takeover enricher failed for %s: %s", entity.domain, exc)
        scan.enricher_errors["takeover"] = str(exc)
        scan.takeover_candidates = []
        return False

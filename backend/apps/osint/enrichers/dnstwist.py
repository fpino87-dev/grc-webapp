"""Typosquatting / brand-monitoring enricher (dnstwist).

Genera permutazioni del dominio (typo, swap, omoglyph, hyphenation, TLD) e
verifica quali hanno un record DNS A attivo: questi sono potenzialmente domini
"sosia" usati per phishing o brand-abuse.

OPZIONALE — la libreria `dnstwist` non è in `requirements.txt` di default. Se non
installata, l'enricher salta silenziosamente (l'OSINT scan non fallisce).
Per attivarlo: `pip install dnstwist`.

Salva risultati in `OsintScan.lookalike_domains` come lista di
`{"domain": str, "fuzzer": str, "ips": [str]}`. Il finding `lookalike_domains`
viene generato dal generator (`findings.py`) se la lista non è vuota.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.osint.models import OsintEntity, OsintScan, OsintSettings

logger = logging.getLogger(__name__)

# Cap difensivi: dnstwist può generare 1000+ permutazioni.
MAX_PERMUTATIONS = 250
MAX_RESULTS_REPORTED = 50
# Cap sui lookup MX di "weaponization": evita di moltiplicare le query DNS quando
# i sosia con A attivo sono molti.
MAX_MX_LOOKUPS = 30
MX_TIMEOUT = 5


def _has_mx(domain: str) -> bool:
    """True se il dominio sosia ha record MX → può ricevere/inviare email (phishing
    via spoofing del brand). Conservativo: in caso di errore ritorna False."""
    import dns.resolver
    try:
        resolver = dns.resolver.Resolver()
        resolver.lifetime = MX_TIMEOUT
        resolver.timeout = MX_TIMEOUT
        ans = resolver.resolve(domain, "MX", raise_on_no_answer=False)
        return bool(list(ans))
    except Exception:
        return False


def run(entity: "OsintEntity", scan: "OsintScan", settings: "OsintSettings") -> bool:
    from apps.osint.validators import assert_public_or_log

    domain = entity.domain
    if not assert_public_or_log(domain, "dnstwist"):
        scan.enricher_errors["dnstwist"] = "non_public_target"
        return False

    try:
        import dnstwist  # type: ignore[import-untyped]
    except ImportError:
        # Opzionale: assenza è normale, non è un errore.
        scan.lookalike_domains = []
        return True

    try:
        # API dnstwist espone Fuzzer + DomainThread/Scanner. Per portabilità
        # tra versioni, usiamo l'entry point pubblico run() quando disponibile.
        results: list[dict] = []
        if hasattr(dnstwist, "run"):
            raw = dnstwist.run(
                domain=domain,
                registered=True,
                format="json",
                threads=4,
                useragent="GRC-OSINT-Scanner/1.0",
            ) or []
        else:
            # Fallback su API legacy: Fuzzer per generare e DnsRecord per resolve.
            fuzz = dnstwist.Fuzzer(domain)
            fuzz.generate()
            raw = list(fuzz.permutations(registered=False))[:MAX_PERMUTATIONS]
            # Senza Scanner non possiamo risolvere; ritorniamo lista vuota.
            scan.lookalike_domains = []
            return True

        for entry in raw:
            d = entry.get("domain") or entry.get("domain-name")
            if not d or d.lower() == domain.lower():
                continue
            ips = entry.get("dns_a") or entry.get("dns-a") or []
            if not ips:
                continue  # solo domini con A attivo
            results.append({
                "domain": d,
                "fuzzer": entry.get("fuzzer", "unknown"),
                "ips": ips[:5] if isinstance(ips, list) else [str(ips)],
            })
            if len(results) >= MAX_RESULTS_REPORTED:
                break

        # Weaponization: marca i sosia con MX configurato (pronti al phishing via
        # email). dnstwist può già fornire `dns_mx`; se assente, lookup diretto
        # (limitato a MAX_MX_LOOKUPS). Il flag alza la severity del finding.
        mx_lookups = 0
        for r in results:
            mx_present = None
            for entry in raw:
                ed = entry.get("domain") or entry.get("domain-name")
                if ed and ed.lower() == r["domain"].lower():
                    raw_mx = entry.get("dns_mx") or entry.get("dns-mx")
                    if raw_mx:
                        mx_present = True
                    break
            if mx_present is None and mx_lookups < MAX_MX_LOOKUPS:
                mx_present = _has_mx(r["domain"])
                mx_lookups += 1
            r["mx"] = bool(mx_present)

        scan.lookalike_domains = results
        return True
    except Exception as exc:
        logger.debug("dnstwist enricher failed for %s: %s", domain, exc)
        scan.enricher_errors["dnstwist"] = str(exc)
        scan.lookalike_domains = []
        return False

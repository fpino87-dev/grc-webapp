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

        scan.lookalike_domains = results
        return True
    except Exception as exc:
        logger.debug("dnstwist enricher failed for %s: %s", domain, exc)
        scan.enricher_errors["dnstwist"] = str(exc)
        scan.lookalike_domains = []
        return False

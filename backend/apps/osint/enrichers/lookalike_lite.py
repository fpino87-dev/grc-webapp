"""Domini sosia senza dipendenze esterne (usato quando dnstwist non c'è).

Genera le varianti più usate per impersonare un dominio — refusi, lettere
doppiate o scambiate, omoglifi, trattini, cambio di TLD — e tiene solo quelle
registrate e attive (record A o MX). Un sosia con MX è pronto per le email di
phishing o per la frode sulle fatture. Solo DNS: nessun contatto con i siti.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.osint.models import OsintEntity, OsintScan, OsintSettings

logger = logging.getLogger(__name__)

MAX_CANDIDATES = 250
MAX_RESULTS = 20
DNS_TIMEOUT = 2.0
TLDS = ["com", "it", "eu", "net", "org", "de", "fr", "co", "info", "biz", "pl", "com.tr"]
HOMOGLYPHS = {"o": ["0"], "0": ["o"], "l": ["1", "i"], "i": ["1", "l"], "e": ["3"], "a": ["4"], "s": ["5"],
              "m": ["rn"], "w": ["vv"], "g": ["q"], "c": ["e"]}
KEYBOARD = {
    "q": "wa", "w": "qes", "e": "wrd", "r": "etf", "t": "ryg", "y": "tuh", "u": "yij", "i": "uok", "o": "ipl",
    "p": "ol", "a": "qsz", "s": "adw", "d": "sfe", "f": "dgr", "g": "fht", "h": "gjy", "j": "hku", "k": "jli",
    "l": "ko", "z": "xa", "x": "zc", "c": "xv", "v": "cb", "b": "vn", "n": "bm", "m": "n",
}


def _split(domain: str) -> tuple[str, str]:
    parts = domain.lower().split(".")
    if len(parts) >= 3 and parts[-2] in {"co", "com", "org", "net", "gov"}:
        return ".".join(parts[:-2]), ".".join(parts[-2:])
    return ".".join(parts[:-1]), parts[-1]


def candidates(domain: str) -> list[str]:
    name, tld = _split(domain)
    if not name or "." in name:
        return []
    names: set[str] = set()
    for i in range(len(name)):
        names.add(name[:i] + name[i + 1:])                      # omissione
        names.add(name[:i] + name[i] + name[i:])                # doppia
        if i < len(name) - 1:
            names.add(name[:i] + name[i + 1] + name[i] + name[i + 2:])  # scambio
            names.add(name[:i + 1] + "-" + name[i + 1:])        # trattino
        for g in HOMOGLYPHS.get(name[i], []):
            names.add(name[:i] + g + name[i + 1:])              # omoglifo
        for k in KEYBOARD.get(name[i], ""):
            names.add(name[:i] + k + name[i + 1:])              # tasto vicino
    names.discard(name)
    names = {n for n in names if n and not n.startswith("-") and not n.endswith("-") and len(n) > 2}
    out = {f"{n}.{tld}" for n in names}
    out |= {f"{name}.{t}" for t in TLDS if t != tld}              # cambio TLD
    out |= {f"{name}-{tld.replace('.', '-')}.com", f"{name}{tld.replace('.', '')}.com"}
    out.discard(domain.lower())
    return sorted(out)[:MAX_CANDIDATES]


def _lookup(domain: str) -> tuple[list[str], list[str]]:
    """(IP A, host MX) del dominio; liste vuote se non risolve."""
    import dns.resolver

    resolver = dns.resolver.Resolver()
    resolver.lifetime = DNS_TIMEOUT
    ips: list[str] = []
    mxs: list[str] = []
    try:
        ips = [r.to_text() for r in resolver.resolve(domain, "A")][:5]
    except Exception:
        pass
    try:
        mxs = [r.exchange.to_text().rstrip(".").lower() for r in resolver.resolve(domain, "MX")][:5]
    except Exception:
        pass
    return ips, mxs


def _probe(domain: str) -> dict | None:
    ips, mxs = _lookup(domain)
    if not ips and not mxs:
        return None
    return {"domain": domain, "fuzzer": "lite", "ips": ips, "mx": bool(mxs), "_mx_hosts": mxs}


RECENT_DAYS = 365
MAX_RDAP_LOOKUPS = 10


def registration_date(domain: str):
    """Data di registrazione via RDAP (None se il registry non la espone)."""
    from apps.osint.enrichers.whois_enr import _query_rdap, _to_date

    try:
        data = _query_rdap(domain) or {}
    except Exception:
        return None
    for ev in data.get("events", []) or []:
        if ev.get("eventAction") == "registration":
            return _to_date(ev.get("eventDate"))
    return None


def mark_recent(found: list[dict]) -> None:
    """Data di registrazione dei sosia con posta: un omonimo registrato da anni
    è quasi sempre un'altra azienda; un sosia nuovo con posta è il segnale di
    phishing o di frode sulle fatture."""
    from datetime import date

    for r in [x for x in found if x.get("mx")][:MAX_RDAP_LOOKUPS]:
        reg = registration_date(r["domain"])
        r["registered"] = reg.isoformat() if reg else None
        r["recent"] = bool(reg and (date.today() - reg).days <= RECENT_DAYS)


def run(entity: "OsintEntity", scan: "OsintScan", settings: "OsintSettings") -> bool:
    try:
        # Le varianti dello stesso titolare (stessi IP o stessi server di posta,
        # es. rossi.it e rossi.com) non sono sosia: si scartano.
        own_ips, own_mx = _lookup(entity.domain)
        with ThreadPoolExecutor(max_workers=8) as pool:
            found = [r for r in pool.map(_probe, candidates(entity.domain)) if r]
        found = [r for r in found if not (set(r["ips"]) & set(own_ips)) and not (set(r["_mx_hosts"]) & set(own_mx))]
        for r in found:
            r.pop("_mx_hosts", None)
        mark_recent(found)
        # prima i sosia recenti con posta, poi quelli con posta
        found.sort(key=lambda r: (not r.get("recent"), not r["mx"], r["domain"]))
        scan.lookalike_domains = found[:MAX_RESULTS]
        return True
    except Exception as exc:
        logger.debug("lookalike_lite failed for %s: %s", entity.domain, exc)
        scan.enricher_errors["lookalike"] = str(exc)[:200]
        scan.lookalike_domains = []
        return False

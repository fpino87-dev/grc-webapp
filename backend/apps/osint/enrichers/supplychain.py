"""Controlli di supply chain: cosa conta davvero su un fornitore.

Tre domande, tutte passive (DNS, log dei certificati, database pubblici —
nessuna scansione dei sistemi del fornitore):

1. il fornitore è compromesso?  → leak site ransomware (ransomware.live),
   violazioni note del suo servizio (HIBP, elenco pubblico per dominio);
2. qualcuno può fingersi il fornitore?  → domini sosia (lookalike_lite),
   dominio falsificabile (DMARC, dai dati DNS già raccolti);
3. espone accessi remoti vulnerabili?  → host di accesso remoto trovati nei
   log CT, verificati con Shodan InternetDB e confrontati con CISA KEV
   (solo fornitori a monitoraggio approfondito).

In più il certificato dei soli servizi del fornitore che usiamo davvero.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from datetime import timedelta
from typing import TYPE_CHECKING

import requests
from django.core.cache import cache
from django.utils import timezone

if TYPE_CHECKING:
    from apps.osint.models import OsintEntity, OsintScan, OsintSettings

logger = logging.getLogger(__name__)

TIMEOUT = 15
UA = {"User-Agent": "GRC-OSINT-Monitor/1.0"}
RANSOMWARE_RECENT_URL = "https://api.ransomware.live/v2/recentvictims"
HIBP_DOMAIN_URL = "https://haveibeenpwned.com/api/v3/breaches"
INTERNETDB_URL = "https://internetdb.shodan.io/{ip}"
KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
CACHE_TTL = 24 * 3600
RANSOMWARE_WINDOW_DAYS = 180
MAX_REMOTE_HOSTS = 12

# Host tipici di accesso remoto / scambio file: è su questi che un fornitore
# con accesso ai nostri sistemi può diventare la porta d'ingresso.
REMOTE_ACCESS_PATTERN = re.compile(
    r"^(vpn|sslvpn|remote|rdp|rdweb|rds|citrix|ctx|netscaler|gateway|gw|fortigate|forti|"
    r"globalprotect|anyconnect|pulse|ivanti|owa|webmail|exchange|mail|sftp|ftp|portal|"
    r"extranet|access|teamviewer|anydesk|vdi|horizon|workspace)[0-9-]*\.",
)
ADMIN_PORTS = {3389: "RDP", 445: "SMB", 23: "Telnet", 5900: "VNC"}

_LEGAL_SUFFIXES = {
    "srl", "srls", "spa", "sas", "snc", "sapa", "scarl", "scrl", "gmbh", "ag", "kg", "ltd", "llc", "inc",
    "corp", "co", "sa", "sarl", "bv", "nv", "oy", "ab", "as", "spzoo", "sp", "zoo", "sl",
}


def normalize_name(name: str) -> str:
    """Nome confrontabile: minuscolo, senza accenti, punteggiatura e forma
    giuridica ("Rossi S.p.A." → "rossi")."""
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s.replace(".", ""))
    words = [w for w in s.split() if w not in _LEGAL_SUFFIXES]
    return " ".join(words).strip()


# ── 1 · Compromissione ───────────────────────────────────────────────────────

def refresh_ransomware_victims() -> int:
    """Scarica le vittime recenti da ransomware.live e le salva in locale.
    Chiamato ogni 6 ore (l'elenco recente copre qualche giorno)."""
    from apps.osint.models import OsintRansomwareVictim
    from django.utils.dateparse import parse_datetime

    try:
        resp = requests.get(RANSOMWARE_RECENT_URL, timeout=30, headers=UA)
        resp.raise_for_status()
        rows = resp.json()
    except Exception as exc:
        logger.warning("ransomware.live non raggiungibile: %s", exc)
        return 0
    saved = 0
    for r in rows if isinstance(rows, list) else []:
        victim = (r.get("victim") or "").strip()[:300]
        group = (r.get("group") or "").strip()[:100]
        discovered = parse_datetime(r.get("discovered") or "") or timezone.now()
        if not victim or not group:
            continue
        domain = (r.get("domain") or "").strip().lower()
        if not domain and re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", victim.lower()):
            domain = victim.lower()
        _, created = OsintRansomwareVictim.objects.update_or_create(
            group=group, victim=victim,
            defaults={"domain": domain[:255], "discovered": discovered, "country": (r.get("country") or "")[:10],
                      "activity": (r.get("activity") or "")[:200], "name_key": normalize_name(victim)},
        )
        saved += int(created)
    return saved


def ransomware_hits(entity: "OsintEntity") -> list[dict]:
    """Corrispondenze del fornitore sui leak site degli ultimi 180 giorni:
    per dominio, o per nome normalizzato identico (almeno 4 caratteri)."""
    from django.db.models import Q

    from apps.osint.models import OsintRansomwareVictim

    since = timezone.now() - timedelta(days=RANSOMWARE_WINDOW_DAYS)
    domain = (entity.domain or "").lower()
    q = Q(domain=domain) | Q(victim__iexact=domain)
    key = normalize_name(entity.display_name)
    if len(key) >= 4:
        q |= Q(name_key=key)
    return [
        {"victim": v.victim, "group": v.group, "discovered": v.discovered.isoformat(), "country": v.country}
        for v in OsintRansomwareVictim.objects.filter(q, discovered__gte=since)[:5]
    ]


def hibp_domain_breaches(domain: str) -> list[dict]:
    """Violazioni pubbliche del servizio con questo dominio (elenco HIBP per
    dominio, gratuito e senza chiave)."""
    ck = f"osint:hibp_domain:{domain}"
    cached = cache.get(ck)
    if cached is not None:
        return cached
    try:
        resp = requests.get(HIBP_DOMAIN_URL, params={"domain": domain}, timeout=TIMEOUT, headers=UA)
        resp.raise_for_status()
        rows = resp.json() or []
    except Exception as exc:
        logger.debug("HIBP breaches per dominio non disponibile per %s: %s", domain, exc)
        return []
    result = [
        {"name": r.get("Name", ""), "date": r.get("BreachDate", ""), "pwn_count": r.get("PwnCount", 0),
         "data_classes": (r.get("DataClasses") or [])[:8]}
        for r in rows if isinstance(r, dict)
    ]
    cache.set(ck, result, CACHE_TTL)
    return result


# ── 3 · Esposizione di accessi remoti ────────────────────────────────────────

def kev_catalog() -> set[str]:
    """CVE del catalogo CISA KEV (vulnerabilità sfruttate attivamente), in cache 24 h."""
    cached = cache.get("osint:kev")
    if cached is not None:
        return set(cached)
    try:
        resp = requests.get(KEV_URL, timeout=30, headers=UA)
        resp.raise_for_status()
        ids = [v.get("cveID") for v in resp.json().get("vulnerabilities", []) if v.get("cveID")]
    except Exception as exc:
        logger.warning("Catalogo CISA KEV non disponibile: %s", exc)
        return set()
    cache.set("osint:kev", ids, CACHE_TTL)
    return set(ids)


def internetdb(ip: str) -> dict:
    ck = f"osint:internetdb:{ip}"
    cached = cache.get(ck)
    if cached is not None:
        return cached
    try:
        resp = requests.get(INTERNETDB_URL.format(ip=ip), timeout=TIMEOUT, headers=UA)
        data = resp.json() if resp.status_code == 200 else {}
    except Exception as exc:
        logger.debug("InternetDB non disponibile per %s: %s", ip, exc)
        return {}
    cache.set(ck, data, CACHE_TTL)
    return data


def remote_access_hosts(entity: "OsintEntity") -> list[str]:
    """Host di accesso remoto del fornitore visti nei log dei certificati."""
    names = set(entity.subdomains.filter(deleted_at__isnull=True).values_list("subdomain", flat=True))
    return sorted(n for n in names if REMOTE_ACCESS_PATTERN.match(n.lower()))[:MAX_REMOTE_HOSTS]


def remote_access(entity: "OsintEntity") -> list[dict]:
    from apps.osint.validators import safe_resolve_public_ip

    kev = kev_catalog()
    out, seen_ips = [], set()
    for host in remote_access_hosts(entity):
        ip = safe_resolve_public_ip(host)
        if not ip or ip in seen_ips:
            continue
        seen_ips.add(ip)
        data = internetdb(ip)
        ports = sorted(data.get("ports") or [])
        vulns = data.get("vulns") or []
        out.append({
            "host": host, "ip": ip, "ports": ports[:20],
            "admin_ports": [ADMIN_PORTS[p] for p in ports if p in ADMIN_PORTS],
            "kev": sorted(v for v in vulns if v in kev)[:10],
            "vulns_count": len(vulns),
        })
    return out


# ── Servizi usati ────────────────────────────────────────────────────────────

def service_checks(entity: "OsintEntity") -> list[dict]:
    """Certificato dei servizi del fornitore che usiamo (portale, SFTP…)."""
    from apps.osint.enrichers.ssl import _get_tls_cert, _parse_cert

    out = []
    for host in (entity.service_hosts or [])[:10]:
        cert = _get_tls_cert(host)
        if not cert:
            out.append({"host": host, "reachable": False, "days_remaining": None, "expiry": None})
            continue
        _valid, expiry, days, _issuer, _wild = _parse_cert(cert)
        out.append({"host": host, "reachable": True, "days_remaining": days,
                    "expiry": expiry.isoformat() if expiry else None})
    return out


def run(entity: "OsintEntity", scan: "OsintScan", settings: "OsintSettings") -> bool:
    """Controlli di supply chain su un fornitore. Il campo della singola fonte
    resta vuoto se la fonte non risponde: non si inventano problemi."""
    try:
        scan.ransomware_hits = ransomware_hits(entity)
        scan.hibp_domain_breaches = hibp_domain_breaches(entity.domain)
        scan.service_checks = service_checks(entity)
        scan.remote_access = remote_access(entity) if entity.deep_monitoring else []
        return True
    except Exception as exc:
        logger.warning("Controlli supply chain falliti per %s: %s", entity.domain, exc)
        scan.enricher_errors["supplychain"] = str(exc)[:200]
        return False

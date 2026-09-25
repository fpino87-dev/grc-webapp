"""Finding engine OSINT.

Differenza con `alerts.py`:
- AlertEngine emette notifiche (snapshot del momento). Una volta acknowledged
  nessuno verifica più che il problema sia ancora presente.
- FindingEngine mantiene una lista persistente di problemi aperti, con stato
  open → in_progress → resolved. Auto-chiude i finding quando lo scan
  successivo conferma che il problema è scomparso.

Questo è il backbone del menù "Risoluzione" lato GRC.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from django.conf import settings as django_settings
from django.utils import timezone

if TYPE_CHECKING:
    from apps.osint.models import OsintEntity, OsintFinding, OsintScan

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Catalogo playbook
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def load_remediation_catalog() -> dict:
    """Carica il catalogo di remediation (cached). Hot-reload solo a riavvio app."""
    base = Path(django_settings.BASE_DIR) / "frameworks" / "osint_remediation.json"
    try:
        with base.open(encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.error("Cannot load OSINT remediation catalog from %s: %s", base, exc)
        return {}


def get_playbook(code: str) -> dict | None:
    return load_remediation_catalog().get(code)


# ---------------------------------------------------------------------------
# Generator: dopo ogni scan, sincronizza i finding aperti con lo stato attuale
# ---------------------------------------------------------------------------

def _detect_finding_codes(entity, scan) -> dict[str, dict]:
    """Ritorna {code: params} dei problemi presenti in questo scan.

    I 'params' vengono salvati nel finding e usati per rendering UI.
    """
    from apps.osint.models import FindingCode, OsintSubdomain, SubdomainStatus
    from apps.osint.posture import expects_mail, expects_web

    detected: dict[str, dict] = {}

    # SSL
    if scan.ssl_valid is True and scan.ssl_days_remaining is not None:
        if scan.ssl_days_remaining <= 0:
            detected[FindingCode.SSL_EXPIRED] = {"expiry_date": str(scan.ssl_expiry_date or "")}
        elif scan.ssl_days_remaining <= 30:
            detected[FindingCode.SSL_EXPIRY] = {
                "days": scan.ssl_days_remaining,
                "issuer": scan.ssl_issuer or "",
                "expiry_date": str(scan.ssl_expiry_date or ""),
            }
    elif scan.ssl_valid is False:
        detected[FindingCode.SSL_EXPIRED] = {"expiry_date": str(scan.ssl_expiry_date or "")}

    # Nessun HTTPS ma il sito risponde in chiaro: è un finding, non una non
    # applicabilità. Un dominio che non risponde a nulla non compare qui.
    if getattr(scan, "http_only", None) is True and expects_web(entity, scan):
        detected[FindingCode.NO_HTTPS] = {}

    # DMARC/SPF — solo con posta accertata (`is True`): su un dominio senza MX
    # l'assenza di SPF/DMARC è la configurazione corretta, non un buco, e su un
    # dominio non sondabile non è dimostrabile nulla.
    if expects_mail(entity, scan):
        if scan.dmarc_present is False:
            detected[FindingCode.DMARC_MISSING] = {}
        elif scan.dmarc_present is True and scan.dmarc_policy == "none":
            detected[FindingCode.DMARC_NONE] = {}

        if scan.spf_present is False:
            detected[FindingCode.SPF_MISSING] = {}
        elif scan.spf_present is True and scan.spf_policy in ("+all", "permerror_multiple", "permerror_lookup"):
            # SPF "broken": +all = autorizza chiunque; permerror_* = MTA non valuta SPF
            detected[FindingCode.SPF_PLUS_ALL] = {"reason": scan.spf_policy}

        # DKIM/MTA-STS: rilevati solo su domini con mail server. `is False` esclude
        # i domini non sondati (None) → nessun finding spurio.
        if getattr(scan, "dkim_present", None) is False:
            detected[FindingCode.DKIM_MISSING] = {}
        if getattr(scan, "mta_sts_present", None) is False:
            detected[FindingCode.MTA_STS_MISSING] = {
                "tls_rpt": bool(getattr(scan, "tls_rpt_present", None)),
            }

    # DNSSEC — segnalato solo se il dominio ha una presenza rilevabile (web o mail).
    # Per domini NXDOMAIN o senza alcun record DNS, dnssec_enabled=False è un
    # artefatto del resolver, non un vero gap di sicurezza.
    _domain_has_presence = (
        scan.ssl_valid is not None
        or scan.mx_present is True
        or scan.spf_present is True
        or scan.dmarc_present is True
    )
    if scan.dnssec_enabled is False and _domain_has_presence:
        detected[FindingCode.DNSSEC_MISSING] = {}

    # Domain expiry
    if scan.domain_expiry_date:
        days = (scan.domain_expiry_date - timezone.localdate()).days
        if days <= 30:
            detected[FindingCode.DOMAIN_EXPIRY_SOON] = {
                "days": days,
                "expiry_date": str(scan.domain_expiry_date),
            }

    # Reputation
    if scan.in_blacklist:
        detected[FindingCode.BLACKLIST] = {"sources": scan.blacklist_sources or []}
    if scan.vt_malicious and scan.vt_malicious > 0:
        detected[FindingCode.VT_MALICIOUS] = {"count": scan.vt_malicious}
    if scan.gsb_status and scan.gsb_status not in ("safe", ""):
        detected[FindingCode.GSB_UNSAFE] = {"status": scan.gsb_status}

    # abuse.ch CTI (CRITICAL). Valorizzati solo se l'enricher ha girato (chiave
    # presente): None → nessun finding spurio.
    if (getattr(scan, "threatfox_iocs", None) or 0) > 0:
        detected[FindingCode.THREATFOX_LISTED] = {
            "count": scan.threatfox_iocs,
            "malware": (getattr(scan, "threatfox_malware", None) or [])[:10],
        }
    if (getattr(scan, "urlhaus_urls", None) or 0) > 0:
        detected[FindingCode.URLHAUS_LISTED] = {"count": scan.urlhaus_urls}

    # Headers HTTP (popolato da enricher http_headers se attivo)
    headers = getattr(scan, "security_headers", None) or {}
    missing_headers = headers.get("missing", []) if isinstance(headers, dict) else []
    if missing_headers:
        detected[FindingCode.HEADERS_MISSING] = {"missing": missing_headers}

    # Lookalike: dal generatore interno solo i sosia registrati di recente con
    # posta (un omonimo registrato da anni è quasi sempre un'altra azienda);
    # i risultati dnstwist, senza data di registrazione, restano come prima.
    lookalikes = [
        d for d in (getattr(scan, "lookalike_domains", None) or [])
        if d.get("recent") or ("recent" not in d and d.get("fuzzer") != "lite")
    ]
    if lookalikes:
        detected[FindingCode.LOOKALIKE] = {"domains": lookalikes[:20]}

    # Subdomain takeover (CRITICAL): CNAME dangling verso servizio cloud dismesso
    takeover = getattr(scan, "takeover_candidates", None) or []
    if takeover:
        detected[FindingCode.SUBDOMAIN_TAKEOVER] = {"candidates": takeover[:20]}

    # CT monitoring (CRITICAL): certificati recenti emessi da CA fuori allowlist.
    # Valorizzato solo quando l'allowlist `ct_expected_issuers` è configurata.
    ct_unexpected = getattr(scan, "ct_unexpected_issuers", None) or []
    if ct_unexpected:
        detected[FindingCode.CT_UNEXPECTED_ISSUER] = {
            "issuers": ct_unexpected[:10],
            "recent_certs": (getattr(scan, "ct_recent_certs", None) or [])[:10],
        }

    # Breach (solo my_domain)
    from apps.osint.models import EntityType
    if entity.entity_type == EntityType.MY_DOMAIN and scan.hibp_breaches and scan.hibp_breaches > 0:
        detected[FindingCode.BREACH] = {
            "count": scan.hibp_breaches,
            "data_types": (scan.hibp_data_types or [])[:5],
        }

    # New subdomain (aggregate)
    pending = OsintSubdomain.objects.filter(
        entity=entity, status=SubdomainStatus.PENDING, deleted_at__isnull=True,
    ).count()
    if pending > 0:
        detected[FindingCode.NEW_SUBDOMAIN] = {"count": pending}

    if entity.entity_type == EntityType.SUPPLIER:
        return _supplier_profile(entity, scan, detected)
    return detected


# Su un fornitore contano tre cose: è compromesso, qualcuno può fingersi lui,
# espone accessi remoti vulnerabili. L'igiene di facciata (certificato del
# sito vetrina, header, DNSSEC, MTA-STS…) confluisce nella Maturità del voto e
# non genera problemi da segnalare.
SUPPLIER_KEEP = {
    "blacklist", "vt_malicious", "gsb_unsafe", "threatfox_listed", "urlhaus_listed",
    "domain_expiry_soon", "lookalike_domains", "subdomain_takeover",
}


def _supplier_profile(entity, scan, detected: dict) -> dict:
    from apps.osint.models import FindingCode

    out = {code: params for code, params in detected.items() if code in SUPPLIER_KEEP}
    if not entity.deep_monitoring:
        out.pop(FindingCode.SUBDOMAIN_TAKEOVER, None)
    # Sosia di un fornitore: contano solo quelli registrati di recente con
    # posta. Un omonimo registrato da anni è quasi sempre un'altra azienda.
    out.pop(FindingCode.LOOKALIKE, None)
    recent = [d for d in (getattr(scan, "lookalike_domains", None) or []) if d.get("recent")]
    if recent:
        out[FindingCode.LOOKALIKE] = {"domains": recent[:20]}

    # Dominio falsificabile: senza DMARC in blocco chiunque può inviare email
    # "da" questo dominio (frode sulle fatture, cambio IBAN).
    if scan.dmarc_present is False or (scan.dmarc_present is True and scan.dmarc_policy == "none"):
        out[FindingCode.DOMAIN_SPOOFABLE] = {
            "dmarc": "missing" if scan.dmarc_present is False else "none",
            "spf": scan.spf_policy or "", "deep": bool(entity.deep_monitoring),
        }

    hits = getattr(scan, "ransomware_hits", None) or []
    if hits:
        out[FindingCode.RANSOMWARE_VICTIM] = {"hits": hits[:5]}

    breaches = [b for b in (getattr(scan, "hibp_domain_breaches", None) or []) if _months_ago(b.get("date")) <= 24]
    if breaches:
        out[FindingCode.SERVICE_BREACH] = {
            "breaches": breaches[:5], "recent": any(_months_ago(b.get("date")) <= 12 for b in breaches),
        }

    remote = getattr(scan, "remote_access", None) or []
    kev = [{"host": r["host"], "kev": r["kev"]} for r in remote if r.get("kev")]
    if kev:
        out[FindingCode.REMOTE_ACCESS_KEV] = {"hosts": kev[:10]}
    admin = [{"host": r["host"], "services": r["admin_ports"]} for r in remote if r.get("admin_ports")]
    if admin:
        out[FindingCode.ADMIN_SERVICE_EXPOSED] = {"hosts": admin[:10]}

    certs = [c for c in (getattr(scan, "service_checks", None) or [])
             if c.get("reachable") and c.get("days_remaining") is not None and c["days_remaining"] <= 14]
    if certs:
        out[FindingCode.SERVICE_CERT] = {"hosts": certs[:10], "expired": any(c["days_remaining"] <= 0 for c in certs)}
    return out


def _months_ago(date_str) -> float:
    from datetime import date
    try:
        d = date.fromisoformat(str(date_str)[:10])
    except ValueError:
        return 999
    return (timezone.localdate() - d).days / 30.4


def _severity_for(code: str, params: dict | None = None) -> str:
    """Mappa code → severity. CRITICAL = action immediata.

    Per alcuni codici la severity è dinamica e dipende dai `params` dello scan:
    es. un dominio lookalike con MX configurato è "armato" per il phishing via
    email e merita CRITICAL, mentre uno con solo un A record attivo resta WARNING.
    """
    from apps.osint.models import AlertSeverity, FindingCode

    params = params or {}
    # Supply chain: severità dipendenti dal contesto.
    if code == FindingCode.DOMAIN_SPOOFABLE:
        # critico per i fornitori critici; per gli altri resta da tenere d'occhio
        return AlertSeverity.CRITICAL if params.get("deep") else AlertSeverity.WARNING
    if code == FindingCode.SERVICE_BREACH:
        return AlertSeverity.CRITICAL if params.get("recent") else AlertSeverity.WARNING
    if code == FindingCode.SERVICE_CERT:
        return AlertSeverity.CRITICAL if params.get("expired") else AlertSeverity.WARNING
    if code == FindingCode.DOMAIN_EXPIRY_SOON and (params.get("days") or 1) <= 0:
        return AlertSeverity.CRITICAL  # dominio scaduto: chi lo registra riceve la posta
    if code in (FindingCode.RANSOMWARE_VICTIM, FindingCode.REMOTE_ACCESS_KEV):
        return AlertSeverity.CRITICAL
    if code == FindingCode.ADMIN_SERVICE_EXPOSED:
        return AlertSeverity.WARNING

    # Lookalike "weaponization": severity in base allo stato del sosia.
    if code == FindingCode.LOOKALIKE:
        domains = (params or {}).get("domains", [])
        if any(d.get("mx") for d in domains if isinstance(d, dict)):
            return AlertSeverity.CRITICAL  # almeno un sosia ha MX → phishing email pronto
        return AlertSeverity.WARNING

    high = {
        FindingCode.SSL_EXPIRED, FindingCode.BLACKLIST, FindingCode.GSB_UNSAFE,
        FindingCode.BREACH, FindingCode.VT_MALICIOUS, FindingCode.SUBDOMAIN_TAKEOVER,
        FindingCode.CT_UNEXPECTED_ISSUER,
        FindingCode.THREATFOX_LISTED, FindingCode.URLHAUS_LISTED,
    }
    medium = {
        FindingCode.SSL_EXPIRY, FindingCode.DMARC_MISSING, FindingCode.SPF_MISSING,
        FindingCode.SPF_PLUS_ALL, FindingCode.DOMAIN_EXPIRY_SOON,
        FindingCode.HEADERS_MISSING, FindingCode.DKIM_MISSING,
    }
    # MTA_STS_MISSING resta INFO (default sotto): è un irrobustimento, non un gap
    # diretto come l'assenza di DKIM/DMARC.
    if code in high:
        return AlertSeverity.CRITICAL
    if code in medium:
        return AlertSeverity.WARNING
    return AlertSeverity.INFO


# Finding ancora da chiudere: anche "segnalato al fornitore" resta aperto
# finché lo scan non lo vede più (auto-resolve).
OPEN_STATUSES = ("open", "acknowledged", "in_progress", "reported")
# Segnalazioni ai fornitori ancora aperte dopo questi giorni: da sollecitare.
SUPPLIER_FOLLOWUP_DAYS = 30


def sync_findings(entity: "OsintEntity", scan: "OsintScan") -> tuple[int, int, int]:
    """Riconcilia i finding aperti per questa entità con la nuova evidenza dello scan.

    - Per ogni codice rilevato: crea il finding se manca; aggiorna scan/last_seen/params se esiste.
    - Per ogni finding aperto NON più rilevato: auto-resolve.
    Ritorna (created, updated, auto_resolved).
    """
    from apps.osint.models import FindingStatus, OsintFinding

    created = updated = resolved = 0
    detected = _detect_finding_codes(entity, scan)

    open_findings = list(
        OsintFinding.objects.filter(entity=entity, status__in=OPEN_STATUSES, deleted_at__isnull=True)
    )
    open_by_code = {f.code: f for f in open_findings}

    # Crea / aggiorna
    for code, params in detected.items():
        existing = open_by_code.get(code)
        if existing is None:
            OsintFinding.objects.create(
                entity=entity,
                scan=scan,
                code=code,
                severity=_severity_for(code, params),
                params=params,
            )
            created += 1
        else:
            existing.scan = scan
            existing.params = params
            existing.severity = _severity_for(code, params)  # severity può cambiare nel tempo
            existing.save(update_fields=["scan", "params", "severity", "last_seen", "updated_at"])
            updated += 1

    # Auto-resolve i finding aperti non più rilevati.
    detected_codes = set(detected.keys())
    for code, finding in open_by_code.items():
        if code in detected_codes:
            continue
        finding.status = FindingStatus.RESOLVED
        finding.resolved_at = timezone.now()
        finding.resolution_note = (finding.resolution_note + "\n[auto] Risolto: il problema non è più rilevato dallo scan.").strip()
        finding.save(update_fields=["status", "resolved_at", "resolution_note", "updated_at"])
        resolved += 1

    return created, updated, resolved


# ---------------------------------------------------------------------------
# Fornitori: segnalazione invece di correzione
# ---------------------------------------------------------------------------

def mark_reported(finding: "OsintFinding", user, note: str = "") -> "OsintFinding":
    """Registra che il problema è stato segnalato al fornitore. La correzione
    spetta al fornitore: qui si traccia la segnalazione (evidenza di
    monitoraggio della supply chain, NIS2 art. 21.2.d) e lo scan successivo
    lo chiude da sé quando non lo rileva più. Ripetibile (sollecito)."""
    from django.core.exceptions import ValidationError

    from django.utils.translation import gettext as _

    from apps.osint.models import EntityType
    from core.audit import log_action

    if finding.entity.entity_type != EntityType.SUPPLIER:
        raise ValidationError(_("Solo i problemi dei fornitori si segnalano: quelli interni si correggono."))
    if finding.status not in OPEN_STATUSES:
        raise ValidationError(_("Il problema non è più aperto."))
    previous = finding.reported_at
    finding.status = "reported"
    finding.reported_at = timezone.now()
    finding.reported_by = user
    finding.report_note = (note or "").strip()[:2000]
    finding.save(update_fields=["status", "reported_at", "reported_by", "report_note", "updated_at"])
    log_action(
        user=user, action_code="osint.finding_reported", level="L2", entity=finding,
        payload={"code": finding.code, "domain": finding.entity.domain, "reminder": previous is not None},
    )
    return finding


def report_overdue(finding: "OsintFinding") -> bool:
    """Segnalato da oltre SUPPLIER_FOLLOWUP_DAYS e ancora rilevato."""
    from datetime import timedelta

    return (
        finding.status == "reported" and finding.reported_at is not None
        and finding.reported_at < timezone.now() - timedelta(days=SUPPLIER_FOLLOWUP_DAYS)
    )

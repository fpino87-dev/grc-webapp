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
    from apps.osint.models import OsintEntity, OsintScan

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

    # DMARC/SPF — solo se il dominio ha mail server
    if scan.mx_present is not False:
        if scan.dmarc_present is False:
            detected[FindingCode.DMARC_MISSING] = {}
        elif scan.dmarc_present is True and scan.dmarc_policy == "none":
            detected[FindingCode.DMARC_NONE] = {}

        if scan.spf_present is False:
            detected[FindingCode.SPF_MISSING] = {}
        elif scan.spf_present is True and scan.spf_policy in ("+all", "permerror_multiple", "permerror_lookup"):
            # SPF "broken": +all = autorizza chiunque; permerror_* = MTA non valuta SPF
            detected[FindingCode.SPF_PLUS_ALL] = {"reason": scan.spf_policy}

    # DNSSEC
    if scan.dnssec_enabled is False:
        detected[FindingCode.DNSSEC_MISSING] = {}

    # Domain expiry
    if scan.domain_expiry_date:
        days = (scan.domain_expiry_date - timezone.now().date()).days
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

    # Headers HTTP (popolato da enricher http_headers se attivo)
    headers = getattr(scan, "security_headers", None) or {}
    missing_headers = headers.get("missing", []) if isinstance(headers, dict) else []
    if missing_headers:
        detected[FindingCode.HEADERS_MISSING] = {"missing": missing_headers}

    # Lookalike
    lookalikes = getattr(scan, "lookalike_domains", None) or []
    if lookalikes:
        detected[FindingCode.LOOKALIKE] = {"domains": lookalikes[:20]}

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

    return detected


def _severity_for(code: str) -> str:
    """Mappa code → severity di default. CRITICAL = action immediata."""
    from apps.osint.models import AlertSeverity, FindingCode
    high = {
        FindingCode.SSL_EXPIRED, FindingCode.BLACKLIST, FindingCode.GSB_UNSAFE,
        FindingCode.BREACH, FindingCode.VT_MALICIOUS,
    }
    medium = {
        FindingCode.SSL_EXPIRY, FindingCode.DMARC_MISSING, FindingCode.SPF_MISSING,
        FindingCode.SPF_PLUS_ALL, FindingCode.DOMAIN_EXPIRY_SOON,
        FindingCode.HEADERS_MISSING, FindingCode.LOOKALIKE,
    }
    if code in high:
        return AlertSeverity.CRITICAL
    if code in medium:
        return AlertSeverity.WARNING
    return AlertSeverity.INFO


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
        OsintFinding.objects.filter(
            entity=entity,
            status__in=[FindingStatus.OPEN, FindingStatus.ACKNOWLEDGED, FindingStatus.IN_PROGRESS],
            deleted_at__isnull=True,
        )
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
                severity=_severity_for(code),
                params=params,
            )
            created += 1
        else:
            existing.scan = scan
            existing.params = params
            existing.severity = _severity_for(code)  # severity può cambiare nel tempo
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

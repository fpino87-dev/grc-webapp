"""Score Engine OSINT — Step 4.

Calcola i 4 score dimensionali e lo score aggregato pesato.
Range 0-100 (0 = ottimo, 100 = critico).

Pesi:
  my_domain:  SSL 25% | DNS 25% | Rep 30% | GRC 20%
  altri:      SSL 30% | DNS 30% | Rep 40% | (GRC non applicabile)
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.osint.models import OsintEntity, OsintScan

logger = logging.getLogger(__name__)


def _score_ssl(scan: "OsintScan", warning_days: int = 60) -> int:
    if scan.ssl_valid is None:
        return 0  # nessun HTTPS rilevato: non applicabile, non penalizzare
    if scan.ssl_valid is False:
        return 100
    days = scan.ssl_days_remaining
    if days is None or days <= 0:
        return 100
    if days <= 14:
        return 90
    if days <= 30:
        return 70
    if days <= warning_days:
        return 40
    if days <= 90:
        return 20
    return 0


def _score_dns(scan: "OsintScan") -> int:
    base = 0
    # SPF e DMARC rilevanti solo se il dominio ha un mail server
    if scan.mx_present is not False:
        if scan.spf_present is False:
            base += 40
        elif scan.spf_policy == "+all":
            base += 20
        if scan.dmarc_present is False:
            base += 30
        elif scan.dmarc_policy == "none":
            base += 15
    return min(base, 100)


def _score_reputation(scan: "OsintScan") -> int:
    base = 0
    gsb = scan.gsb_status or ""
    if gsb and gsb != "safe":
        return 100  # esce subito

    if scan.in_blacklist:
        base += 60

    vt = scan.vt_malicious or 0
    if vt > 5:
        base += 40
    elif vt > 0:
        base += 20

    abuse = scan.abuseipdb_score or 0
    if abuse > 50:
        base += 30
    elif abuse > 20:
        base += 15

    pulses = scan.otx_pulses or 0
    if pulses > 5:
        base += 20
    elif pulses > 0:
        base += 10

    return min(base, 100)


def _score_grc(entity: "OsintEntity", scan: "OsintScan") -> int:
    """Applicabile solo a entity_type='my_domain'."""
    from apps.osint.models import EntityType
    if entity.entity_type != EntityType.MY_DOMAIN:
        return 0

    base = 0
    if entity.is_nis2_critical:
        base += 20

    # Rischi aperti collegati al plant sorgente
    try:
        from apps.risk.models import RiskAssessment
        open_risks = RiskAssessment.objects.filter(
            asset__plant_id=entity.source_id,
            status__in=["in_lavorazione", "bozza"],
            deleted_at__isnull=True,
        ).count()
        if open_risks >= 3:
            base += 40
        elif open_risks >= 1:
            base += 20
    except Exception:
        pass

    # Gap controlli (non compliant) collegati al plant
    try:
        from apps.controls.models import ControlInstance
        gap_controls = ControlInstance.objects.filter(
            plant_id=entity.source_id,
            status__in=["non_conforme", "parziale"],
            deleted_at__isnull=True,
        ).count()
        if gap_controls >= 5:
            base += 40
        elif gap_controls >= 1:
            base += 20
    except Exception:
        pass

    return min(base, 100)


def compute_scores(entity: "OsintEntity", scan: "OsintScan") -> None:
    """Calcola e scrive i 4 score + score_total nel scan (non salva — il chiamante salva)."""
    from apps.osint.models import EntityType, OsintSettings

    settings = OsintSettings.load()
    ssl = _score_ssl(scan, warning_days=settings.ssl_expiry_warning_days)
    dns = _score_dns(scan)
    rep = _score_reputation(scan)
    grc = _score_grc(entity, scan)

    scan.score_ssl = ssl
    scan.score_dns = dns
    scan.score_reputation = rep
    scan.score_grc_context = grc

    if entity.entity_type == EntityType.MY_DOMAIN:
        total = (ssl * 0.25) + (dns * 0.25) + (rep * 0.30) + (grc * 0.20)
    else:
        # GRC non applicabile → pesi redistribuiti SSL 30% | DNS 30% | Rep 40%
        total = (ssl * 0.30) + (dns * 0.30) + (rep * 0.40)

    scan.score_total = round(total)


def score_delta(entity: "OsintEntity", current_scan: "OsintScan") -> int:
    """Delta rispetto al penultimo scan. Positivo = peggiorato, negativo = migliorato."""
    from apps.osint.models import OsintScan
    prev = (
        OsintScan.objects.filter(entity=entity, status="completed")
        .exclude(pk=current_scan.pk)
        .order_by("-scan_date")
        .first()
    )
    if prev is None:
        return 0
    return current_scan.score_total - prev.score_total


def classify_score(score: int) -> str:
    """Ritorna 'critical' | 'warning' | 'attention' | 'ok'."""
    if score >= 70:
        return "critical"
    if score >= 50:
        return "warning"
    if score >= 30:
        return "attention"
    return "ok"

"""Alert Engine OSINT — Step 5.

Dopo ogni scan: valuta 7 trigger, genera OsintAlert senza duplicati,
crea automaticamente Incident (my_domain+critical) o Task (supplier+critical/warning).
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from apps.osint.models import OsintEntity, OsintScan, OsintSettings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers interni
# ---------------------------------------------------------------------------

def _prev_scan(entity: "OsintEntity", current_scan: "OsintScan"):
    from apps.osint.models import OsintScan, ScanStatus
    return (
        OsintScan.objects.filter(entity=entity, status=ScanStatus.COMPLETED)
        .exclude(pk=current_scan.pk)
        .order_by("-scan_date")
        .first()
    )


def _has_active_alert(entity: "OsintEntity", alert_type: str) -> bool:
    from apps.osint.models import OsintAlert, AlertStatus
    return OsintAlert.objects.filter(
        entity=entity,
        alert_type=alert_type,
        status__in=[AlertStatus.NEW, AlertStatus.ACKNOWLEDGED, AlertStatus.PENDING_ESCALATION],
    ).exists()


def _create_alert(entity, scan, alert_type, severity, description) -> "OsintAlert":
    from apps.osint.models import OsintAlert
    alert = OsintAlert.objects.create(
        entity=entity,
        scan=scan,
        alert_type=alert_type,
        severity=severity,
        description=description,
    )
    logger.info("OSINT alert created: %s %s for %s", severity, alert_type, entity.domain)
    return alert


# ---------------------------------------------------------------------------
# 7 trigger
# ---------------------------------------------------------------------------

def _trigger_score_critical(entity, scan, prev, settings, created_alerts):
    from apps.osint.models import AlertType, AlertSeverity
    thresh = settings.score_threshold_critical
    if scan.score_total < thresh:
        return
    # Solo primo rilevamento (prev sotto soglia o nessun prev)
    if prev and prev.score_total >= thresh:
        return
    if _has_active_alert(entity, AlertType.SCORE_CRITICAL):
        return
    alert = _create_alert(
        entity, scan,
        AlertType.SCORE_CRITICAL, AlertSeverity.CRITICAL,
        f"Score OSINT critico: {scan.score_total}/100 (soglia: {thresh}). Richiede verifica immediata.",
    )
    created_alerts.append(alert)


def _trigger_score_degraded(entity, scan, prev, settings, created_alerts):
    from apps.osint.models import AlertType, AlertSeverity
    if prev is None:
        return
    delta = scan.score_total - prev.score_total
    if delta < 20:
        return
    if _has_active_alert(entity, AlertType.SCORE_DEGRADED):
        return
    alert = _create_alert(
        entity, scan,
        AlertType.SCORE_DEGRADED, AlertSeverity.WARNING,
        f"Score OSINT peggiorato di {delta} punti rispetto alla rilevazione precedente "
        f"({prev.score_total} → {scan.score_total}).",
    )
    created_alerts.append(alert)


def _trigger_ssl(entity, scan, settings, created_alerts):
    from apps.osint.models import AlertType, AlertSeverity
    days = scan.ssl_days_remaining
    valid = scan.ssl_valid
    domain = entity.domain
    issuer_info = f" | CA: {scan.ssl_issuer}" if scan.ssl_issuer else ""

    if not valid or (days is not None and days <= 0):
        if not _has_active_alert(entity, AlertType.SSL_EXPIRED):
            if scan.ssl_expiry_date:
                desc = (
                    f"Certificato SSL scaduto il {scan.ssl_expiry_date}{issuer_info}. "
                    f"Dominio: {domain}. Rinnovare il certificato per ripristinare l'accesso HTTPS."
                )
            else:
                desc = (
                    f"Porta 443 non raggiungibile o nessun certificato SSL su {domain}. "
                    f"Verificare che il server risponda su HTTPS e che il certificato sia installato."
                )
            alert = _create_alert(entity, scan, AlertType.SSL_EXPIRED, AlertSeverity.CRITICAL, desc)
            created_alerts.append(alert)
    elif days is not None and days <= 30:
        if not _has_active_alert(entity, AlertType.SSL_EXPIRY):
            alert = _create_alert(
                entity, scan,
                AlertType.SSL_EXPIRY, AlertSeverity.WARNING,
                f"Certificato SSL in scadenza tra {days} giorni (entro il {scan.ssl_expiry_date}){issuer_info}. "
                f"Dominio: {domain}.",
            )
            created_alerts.append(alert)


def _trigger_blacklist(entity, scan, prev, settings, created_alerts):
    from apps.osint.models import AlertType, AlertSeverity
    if not scan.in_blacklist:
        return
    if prev and prev.in_blacklist:
        return  # già era in blacklist → non nuovo
    if _has_active_alert(entity, AlertType.BLACKLIST_NEW):
        return
    sources = ", ".join(scan.blacklist_sources or []) or "sconosciuta"
    alert = _create_alert(
        entity, scan,
        AlertType.BLACKLIST_NEW, AlertSeverity.CRITICAL,
        f"Dominio rilevato in blacklist (sorgente: {sources}). Possibile compromissione.",
    )
    created_alerts.append(alert)


def _trigger_dmarc(entity, scan, settings, created_alerts):
    from apps.osint.models import AlertType, AlertSeverity
    if scan.dmarc_present is not False:
        return
    if _has_active_alert(entity, AlertType.DMARC_MISSING):
        return
    alert = _create_alert(
        entity, scan,
        AlertType.DMARC_MISSING, AlertSeverity.WARNING,
        "Nessun record DMARC configurato. Il dominio è vulnerabile al phishing via spoofing email.",
    )
    created_alerts.append(alert)


def _trigger_new_subdomain(entity, scan, settings, created_alerts):
    """Alert per ogni nuovo sottodominio in pending — solo info, no routing."""
    from apps.osint.models import AlertType, AlertSeverity, OsintSubdomain, SubdomainStatus
    pending = OsintSubdomain.objects.filter(
        entity=entity,
        status=SubdomainStatus.PENDING,
    ).count()
    if pending == 0:
        return
    # Un solo alert attivo aggregato per tipo
    if _has_active_alert(entity, AlertType.NEW_SUBDOMAIN):
        return
    alert = _create_alert(
        entity, scan,
        AlertType.NEW_SUBDOMAIN, AlertSeverity.INFO,
        f"{pending} nuovo/i sottodominio/i rilevato/i in attesa di classificazione.",
    )
    created_alerts.append(alert)


def _trigger_breach(entity, scan, prev, settings, created_alerts):
    from apps.osint.models import AlertType, AlertSeverity, EntityType
    if entity.entity_type != EntityType.MY_DOMAIN:
        return
    if not (scan.hibp_breaches and scan.hibp_breaches > 0):
        return
    prev_breaches = prev.hibp_breaches if prev else 0
    if prev_breaches and prev_breaches > 0:
        return  # già noto
    if _has_active_alert(entity, AlertType.BREACH_FOUND):
        return
    types = ", ".join(scan.hibp_data_types[:5]) if scan.hibp_data_types else "N/D"
    alert = _create_alert(
        entity, scan,
        AlertType.BREACH_FOUND, AlertSeverity.CRITICAL,
        f"Rilevato/i {scan.hibp_breaches} breach su HIBP per questo dominio. "
        f"Dati esposti: {types}.",
    )
    created_alerts.append(alert)


# ---------------------------------------------------------------------------
# Routing alert → Incidenti / Task
# ---------------------------------------------------------------------------

def _has_ot_asset_linked(entity: "OsintEntity") -> bool:
    """True se il fornitore gestisce asset OT/IT nel nostro inventario."""
    from apps.assets.models import AssetOT, AssetIT
    sup_id = entity.source_id
    # Cerca asset collegati al fornitore (non c'è FK diretta — cerca per nome vendor se supplier)
    # Per ora logica semplificata: se source_module=suppliers cerca asset OT dello stesso plant
    return False  # Placeholder — espandibile con relazione fornitore↔asset


def _route_alert(alert: "OsintAlert", entity: "OsintEntity") -> None:
    from apps.osint.models import EntityType, AlertSeverity, AlertStatus, AlertType

    # new_subdomain → solo notifica dashboard, no routing
    if alert.alert_type == AlertType.NEW_SUBDOMAIN:
        return

    severity = alert.severity

    if entity.entity_type == EntityType.MY_DOMAIN and severity == AlertSeverity.CRITICAL:
        _create_incident(alert, entity)

    elif entity.entity_type in (EntityType.SUPPLIER, EntityType.ASSET):
        # Solo alert CRITICAL → task automatico; WARNING rimane alert manuale
        if severity == AlertSeverity.CRITICAL:
            if _has_ot_asset_linked(entity):
                alert.status = AlertStatus.PENDING_ESCALATION
                alert.save(update_fields=["status", "updated_at"])
            else:
                _create_task(alert, entity)


def _severity_to_incident(severity: str) -> str:
    return {"critical": "critica", "warning": "alta", "info": "media"}.get(severity, "media")


def _create_incident(alert: "OsintAlert", entity: "OsintEntity") -> None:
    from apps.incidents.models import Incident
    from apps.plants.models import Plant

    try:
        plant = Plant.objects.get(pk=entity.source_id)
    except Plant.DoesNotExist:
        logger.warning("Cannot create incident: plant %s not found for entity %s", entity.source_id, entity.domain)
        return

    try:
        incident = Incident.objects.create(
            plant=plant,
            title=f"OSINT: {alert.get_alert_type_display()} su {entity.display_name}",
            description=(
                f"[Generato automaticamente dal modulo OSINT]\n\n"
                f"Dominio: {entity.domain}\n"
                f"Tipo alert: {alert.get_alert_type_display()}\n\n"
                f"{alert.description}"
            ),
            detected_at=timezone.now(),
            severity=_severity_to_incident(alert.severity),
            nis2_notifiable="da_valutare",
            status="aperto",
        )
        alert.linked_incident_id = incident.pk
        alert.save(update_fields=["linked_incident_id", "updated_at"])
        logger.info("OSINT → Incident created: %s for alert %s", incident.pk, alert.pk)
    except Exception as exc:
        logger.error("Failed to create incident for OSINT alert %s: %s", alert.pk, exc)


def _create_task(alert: "OsintAlert", entity: "OsintEntity") -> None:
    from apps.tasks.models import Task
    from apps.osint.models import AlertSeverity

    priority = "alta" if alert.severity == AlertSeverity.CRITICAL else "media"

    try:
        task = Task.objects.create(
            title=f"OSINT: {alert.get_alert_type_display()} — {entity.display_name}",
            description=(
                f"[Generato automaticamente dal modulo OSINT]\n\n"
                f"Dominio: {entity.domain}\n"
                f"Tipo alert: {alert.get_alert_type_display()}\n\n"
                f"{alert.description}"
            ),
            priority=priority,
            due_date=(timezone.now() + timedelta(days=14)).date(),
            source="manuale",
            source_module="osint",
            source_id=alert.pk,
            status="aperto",
        )
        alert.linked_task_id = task.pk
        alert.save(update_fields=["linked_task_id", "updated_at"])
        logger.info("OSINT → Task created: %s for alert %s", task.pk, alert.pk)
    except Exception as exc:
        logger.error("Failed to create task for OSINT alert %s: %s", alert.pk, exc)


# ---------------------------------------------------------------------------
# Entry point principale
# ---------------------------------------------------------------------------

def run_alerts(
    entity: "OsintEntity",
    scan: "OsintScan",
    settings: "OsintSettings",
) -> list["OsintAlert"]:
    """Valuta tutti i trigger, crea alert e fa il routing. Ritorna la lista degli alert creati."""
    prev = _prev_scan(entity, scan)
    created: list = []

    _trigger_score_critical(entity, scan, prev, settings, created)
    _trigger_score_degraded(entity, scan, prev, settings, created)
    _trigger_ssl(entity, scan, settings, created)
    _trigger_blacklist(entity, scan, prev, settings, created)
    _trigger_dmarc(entity, scan, settings, created)
    _trigger_new_subdomain(entity, scan, settings, created)
    _trigger_breach(entity, scan, prev, settings, created)

    for alert in created:
        _route_alert(alert, entity)

    return created

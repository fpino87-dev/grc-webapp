"""Alert Engine OSINT — Step 5.

Dopo ogni scan: valuta i trigger, genera OsintAlert senza duplicati,
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

    if valid is False or (days is not None and days <= 0):
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
    if scan.mx_present is False:
        return  # nessun mail server: DMARC non applicabile
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


def _trigger_takeover(entity, scan, settings, created_alerts):
    """Alert CRITICAL su possibili subdomain takeover (CNAME dangling)."""
    from apps.osint.models import AlertType, AlertSeverity
    candidates = getattr(scan, "takeover_candidates", None) or []
    if not candidates:
        return
    if _has_active_alert(entity, AlertType.SUBDOMAIN_TAKEOVER):
        return
    subs = ", ".join(c.get("subdomain", "?") for c in candidates[:5])
    suffix = "…" if len(candidates) > 5 else ""
    alert = _create_alert(
        entity, scan,
        AlertType.SUBDOMAIN_TAKEOVER, AlertSeverity.CRITICAL,
        f"Possibile subdomain takeover su {len(candidates)} sottodominio/i ({subs}{suffix}): "
        f"il record CNAME punta a un servizio cloud dismesso e rivendicabile da un attaccante. "
        f"Rimuovere il record DNS o riprendere possesso della risorsa.",
    )
    created_alerts.append(alert)


def _trigger_ct_unexpected(entity, scan, settings, created_alerts):
    """Alert CRITICAL: certificati recenti emessi da CA fuori allowlist (CT)."""
    from apps.osint.models import AlertType, AlertSeverity
    issuers = getattr(scan, "ct_unexpected_issuers", None) or []
    if not issuers:
        return
    if _has_active_alert(entity, AlertType.CT_UNEXPECTED_ISSUER):
        return
    shown = ", ".join(issuers[:3])
    suffix = "…" if len(issuers) > 3 else ""
    alert = _create_alert(
        entity, scan,
        AlertType.CT_UNEXPECTED_ISSUER, AlertSeverity.CRITICAL,
        f"Rilevato/i certificato/i recente/i nei log Certificate Transparency emesso/i "
        f"da CA non presenti nell'allowlist attesa ({shown}{suffix}). Possibile "
        f"mis-issuance, shadow IT o infrastruttura malevola che usa il dominio. "
        f"Verificare la legittimità dei certificati e, se non autorizzati, avviare "
        f"la revoca e l'analisi.",
    )
    created_alerts.append(alert)


def _trigger_abusech(entity, scan, settings, created_alerts):
    """Alert CRITICAL su match abuse.ch (ThreatFox IoC / URLhaus malware URL).

    Emessi solo se l'enricher ha trovato qualcosa (count > 0). Un solo alert
    attivo per tipo (de-dup via `_has_active_alert`)."""
    from apps.osint.models import AlertType, AlertSeverity

    iocs = getattr(scan, "threatfox_iocs", None) or 0
    if iocs > 0 and not _has_active_alert(entity, AlertType.THREATFOX_LISTED):
        malware = ", ".join((getattr(scan, "threatfox_malware", None) or [])[:5]) or "N/D"
        alert = _create_alert(
            entity, scan,
            AlertType.THREATFOX_LISTED, AlertSeverity.CRITICAL,
            f"Rilevato/i {iocs} indicatore/i di compromissione (IoC) su abuse.ch ThreatFox "
            f"per il dominio o il suo IP. Famiglie malware associate: {malware}. "
            f"Indica probabile coinvolgimento in infrastruttura malevola attiva "
            f"(C2/botnet/malware): avviare incident response e verificare l'host.",
        )
        created_alerts.append(alert)

    urls = getattr(scan, "urlhaus_urls", None) or 0
    if urls > 0 and not _has_active_alert(entity, AlertType.URLHAUS_LISTED):
        alert = _create_alert(
            entity, scan,
            AlertType.URLHAUS_LISTED, AlertSeverity.CRITICAL,
            f"abuse.ch URLhaus segnala {urls} URL malevolo/i noto/i sull'host: il dominio "
            f"distribuisce (o ha distribuito) payload malware. Possibile compromissione "
            f"del sito/hosting: isolare i servizi, rimuovere i contenuti malevoli e "
            f"verificare l'integrità del server.",
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
    """True se il fornitore manutiene almeno un asset OT nel nostro inventario.

    Un alert CRITICAL su un fornitore che ha accesso remoto a impianti OT non va
    auto-gestito con un Task: viene messo in `PENDING_ESCALATION` per revisione
    umana (il foothold OT alza la posta). Il legame è il FK
    `Asset.maintainer_supplier`. Significativo solo per entità di tipo fornitore.
    """
    from apps.osint.models import SourceModule
    from apps.assets.models import AssetOT

    if entity.source_module != SourceModule.SUPPLIERS:
        return False
    return AssetOT.objects.filter(
        maintainer_supplier_id=entity.source_id,
        deleted_at__isnull=True,
    ).exists()


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


def _entity_plant(entity: "OsintEntity"):
    """Plant associato all'entità per lo scope delle notifiche M19.

    Solo le entità `my_domain` mappano 1:1 a un Plant (`source_id` = plant pk).
    Per fornitori/asset il legame con un singolo plant è ambiguo (M2M o nessuno):
    in quel caso ritorna None e il resolver notifica i titolari di ruolo a livello
    org. Best-effort: errori di lookup → None."""
    from apps.osint.models import EntityType
    if entity.entity_type != EntityType.MY_DOMAIN:
        return None
    try:
        from apps.plants.models import Plant
        return Plant.objects.filter(pk=entity.source_id, deleted_at__isnull=True).first()
    except Exception as exc:  # pragma: no cover - difensivo
        logger.debug("OSINT plant lookup failed for %s: %s", entity.domain, exc)
        return None


def _notify_critical_alerts(entity: "OsintEntity", created_alerts: list) -> None:
    """Invia notifica M19 (`osint_critical`) per gli alert CRITICAL appena creati.

    Best-effort: schedulata su `transaction.on_commit` così parte solo dopo il
    commit (niente email per uno scan poi annullato) e non blocca mai lo scan.
    Un fallimento del resolver/email viene loggato (regola P0-3: niente pass muto),
    non propagato."""
    from django.db import transaction
    from apps.osint.models import AlertSeverity

    critical = [a for a in created_alerts if a.severity == AlertSeverity.CRITICAL]
    if not critical:
        return

    plant = _entity_plant(entity)

    def _fire():
        from apps.notifications.resolver import fire_notification
        for alert in critical:
            try:
                fire_notification(
                    "osint_critical",
                    plant=plant,
                    context={"alert": alert, "entity": entity},
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "OSINT M19 notify failed (alert=%s type=%s): %s",
                    alert.pk, alert.alert_type, exc,
                )

    transaction.on_commit(_fire)


def _system_user():
    """Utente di sistema a cui attribuire l'audit delle azioni automatiche OSINT
    (creazione incidenti/task da alert). Primo superuser attivo, o None."""
    from django.contrib.auth import get_user_model
    return (
        get_user_model().objects.filter(is_superuser=True, is_active=True)
        .order_by("date_joined").first()
    )


def _audit(action_code: str, entity, payload: dict) -> None:
    """Scrive nell'audit trail (regola architetturale #3). Best-effort: se non
    c'è un utente di sistema o log_action fallisce, non blocca lo scan."""
    from core.audit import log_action
    user = _system_user()
    if user is None:
        logger.warning("OSINT audit skipped (%s): nessun superuser di sistema", action_code)
        return
    try:
        log_action(user=user, action_code=action_code, level="L2", entity=entity, payload=payload)
    except Exception as exc:  # pragma: no cover
        logger.debug("OSINT audit log failed (%s): %s", action_code, exc)


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
        _audit("osint.incident_created", incident, {
            "incident_id": str(incident.pk),
            "alert_id": str(alert.pk),
            "alert_type": alert.alert_type,
            "domain": entity.domain,
            "auto_generated": True,
        })
        logger.info("OSINT → Incident created: %s for alert %s", incident.pk, alert.pk)
    except Exception as exc:
        logger.error("Failed to create incident for OSINT alert %s: %s", alert.pk, exc)


def _create_task(alert: "OsintAlert", entity: "OsintEntity") -> None:
    # Business logic di creazione task centralizzata in M08 (regola #2): usiamo
    # il service invece di scrivere direttamente sul modello Task.
    from apps.tasks.services import create_task
    from apps.osint.models import AlertSeverity

    priority = "alta" if alert.severity == AlertSeverity.CRITICAL else "media"

    try:
        task = create_task(
            plant=None,
            title=f"OSINT: {alert.get_alert_type_display()} — {entity.display_name}",
            description=(
                f"[Generato automaticamente dal modulo OSINT]\n\n"
                f"Dominio: {entity.domain}\n"
                f"Tipo alert: {alert.get_alert_type_display()}\n\n"
                f"{alert.description}"
            ),
            priority=priority,
            source_module="osint",
            source_id=alert.pk,
            due_date=(timezone.now() + timedelta(days=14)).date(),
        )
        alert.linked_task_id = task.pk
        alert.save(update_fields=["linked_task_id", "updated_at"])
        _audit("osint.task_created", task, {
            "task_id": str(task.pk),
            "alert_id": str(alert.pk),
            "alert_type": alert.alert_type,
            "domain": entity.domain,
            "auto_generated": True,
        })
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
    _trigger_takeover(entity, scan, settings, created)
    _trigger_ct_unexpected(entity, scan, settings, created)
    _trigger_abusech(entity, scan, settings, created)
    _trigger_breach(entity, scan, prev, settings, created)

    for alert in created:
        _route_alert(alert, entity)

    # Notifica M19 best-effort per gli alert critici (dopo il routing, così
    # eventuali Incident/Task linkati esistono già al momento dell'invio).
    _notify_critical_alerts(entity, created)

    return created

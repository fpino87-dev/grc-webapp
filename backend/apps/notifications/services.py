import logging
from typing import Tuple

from django.core.mail import EmailMultiAlternatives, get_connection

logger = logging.getLogger(__name__)


def _build_connection(config, fail_silently=False):
    """Costruisce connessione SMTP da un oggetto config.
    Se use_auth=False (relay senza autenticazione) non passa credenziali
    → Django non invia il comando AUTH."""
    return get_connection(
        backend="django.core.mail.backends.smtp.EmailBackend",
        host=config.host,
        port=config.port,
        username=config.username if config.use_auth else None,
        password=config.password if config.use_auth else None,
        use_tls=config.use_tls,
        use_ssl=config.use_ssl,
        fail_silently=fail_silently,
    )


def _get_connection():
    """
    Restituisce connessione SMTP dalla config DB.
    Fallback ai settings Django se nessuna config attiva.
    """
    from .models import EmailConfiguration

    config = EmailConfiguration.get_active()
    if not config:
        return None  # usa settings Django di default

    return _build_connection(config)


def send_grc_email(
    subject: str,
    body: str,
    recipients: list[str],
    html_body: str = "",
    cc: list[str] | None = None,
) -> bool:
    """
    Invia email GRC usando config da DB.

    `recipients` -> destinatari diretti (TO).
    `cc` -> lista opzionale di indirizzi in copia conoscenza.

    Restituisce True se inviata, False se fallita.
    """
    if not recipients:
        return False

    from .models import EmailConfiguration

    config = EmailConfiguration.get_active()
    from_email = config.from_email if config else "GRC Platform <noreply@grc.local>"

    cc_list = [addr for addr in (cc or []) if addr]

    try:
        connection = _get_connection()
        msg = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=from_email,
            to=recipients,
            cc=cc_list or None,
            connection=connection,
        )
        if html_body:
            msg.attach_alternative(html_body, "text/html")
        msg.send()
        logger.info(
            "Email inviata a %d destinatari (cc=%d): %s",
            len(recipients), len(cc_list), subject,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Errore invio email a %d destinatari (cc=%d) [%s]: %s",
            len(recipients), len(cc_list), subject, exc,
        )
        return False


def test_email_connection(config, test_recipient: str = "") -> Tuple[bool, str]:
    """
    Testa la configurazione SMTP inviando una mail di prova.
    test_recipient: indirizzo a cui inviare (obbligatorio).
    Restituisce (success, error_message).
    """
    from django.utils import timezone

    recipient = test_recipient.strip() if test_recipient else ""
    if not recipient:
        return False, "Specifica un indirizzo destinatario per il test."

    try:
        connection = _build_connection(config)
        msg = EmailMultiAlternatives(
            subject="[GRC] Test configurazione email",
            body=(
                "Configurazione email GRC verificata con successo.\n"
                f"Provider: {config.provider}\n"
                f"Host: {config.host}:{config.port}\n"
                f"Data test: {timezone.now().strftime('%d/%m/%Y %H:%M')}"
            ),
            from_email=config.from_email,
            to=[recipient],
            connection=connection,
        )
        msg.send()
        config.last_test_at = timezone.now()
        config.last_test_ok = True
        config.last_test_error = ""
        config.save(
            update_fields=[
                "last_test_at",
                "last_test_ok",
                "last_test_error",
                "updated_at",
            ]
        )
        return True, ""
    except Exception as exc:  # noqa: BLE001
        error_msg = str(exc)[:500]
        from django.utils import timezone

        config.last_test_at = timezone.now()
        config.last_test_ok = False
        config.last_test_error = error_msg
        config.save(
            update_fields=[
                "last_test_at",
                "last_test_ok",
                "last_test_error",
                "updated_at",
            ]
        )
        logger.error("Errore test configurazione email: %s", exc)
        return False, error_msg


# ── Funzioni notifica specifiche ──────────────────────────


def notify_task_assigned(task, user_email: str):
    send_grc_email(
        subject=f"[GRC] Nuovo task: {task.title}",
        body=(
            "Ti è stato assegnato un task nel sistema GRC.\n\n"
            f"Titolo:    {task.title}\n"
            f"Priorità:  {task.priority}\n"
            f"Scadenza:  {task.due_date or 'Non definita'}\n"
            f"Plant:     {task.plant.name if task.plant else '—'}\n"
        ),
        recipients=[user_email],
    )


def notify_finding_major(finding, recipients: list[str]):
    send_grc_email(
        subject=f"[GRC] 🚨 Major NC: {finding.title}",
        body=(
            "È stato registrato un Major Non Conformity.\n\n"
            f"Titolo:    {finding.title}\n"
            f"Auditor:   {getattr(finding, 'auditor_name', '')}\n"
            f"Scadenza:  {finding.response_deadline}\n"
            f"Plant:     {finding.audit_prep.plant.name}\n\n"
            "Azione richiesta entro 30 giorni."
        ),
        recipients=recipients,
    )


def notify_risk_red(assessment, recipients: list[str]):
    send_grc_email(
        subject=f"[GRC] 🔴 Rischio critico: {assessment.name or assessment.asset}",
        body=(
            "Risk assessment ha superato la soglia critica.\n\n"
            f"Plant:  {assessment.plant.name}\n"
            f"Score:  {assessment.score}/25\n"
            f"Asset:  {assessment.asset.name if assessment.asset else '—'}\n\n"
            "Definire piano di mitigazione entro 15 giorni."
        ),
        recipients=recipients,
    )


def notify_incident_nis2(incident, recipients: list[str]):
    send_grc_email(
        subject=f"[GRC] ⚠️ Incidente NIS2: {incident.title}",
        body=(
            "Incidente potenzialmente soggetto a notifica NIS2.\n\n"
            f"Titolo:    {incident.title}\n"
            f"Severità:  {incident.severity}\n"
            f"Rilevato:  {incident.detected_at}\n"
            f"Plant:     {incident.plant.name}\n\n"
            "Timer 24h per notifica preliminare in corso."
        ),
        recipients=recipients,
    )


def notify_osint_alert(alert, entity, recipients: list[str]):
    """
    Alert OSINT critico su esposizione esterna (SSL scaduto, blacklist, breach,
    subdomain takeover, score critico). Contenuto qui; destinatari risolti dal
    chiamante via resolver. Non logga il dominio nei log di sistema (regola #11):
    send_grc_email logga solo conteggi.
    """
    send_grc_email(
        subject=f"[GRC] 🛰️ OSINT critico: {alert.get_alert_type_display()} — {entity.display_name}",
        body=(
            "Il monitoraggio OSINT ha rilevato un problema critico sull'esposizione "
            "esterna di un'entità monitorata.\n\n"
            f"Entità:    {entity.display_name}\n"
            f"Dominio:   {entity.domain}\n"
            f"Tipo:      {alert.get_alert_type_display()}\n"
            f"Severità:  {alert.get_severity_display()}\n\n"
            f"{alert.description}\n\n"
            "Accedi al modulo OSINT → Risoluzione per la guida di remediation."
        ),
        recipients=recipients,
    )


def notify_role_expiring(assignment, days_left: int, recipients: list[str]):
    send_grc_email(
        subject=f"[GRC] Ruolo in scadenza: {assignment.role}",
        body=(
            f"Il ruolo {assignment.role} di "
            f"{assignment.user.get_full_name() or assignment.user.email} "
            f"scade tra {days_left} giorni ({assignment.valid_until}).\n\n"
            "Accedi a Governance per rinnovare o sostituire."
        ),
        recipients=recipients,
    )


def notify_evidence_expired(instance, recipients: list[str]):
    send_grc_email(
        subject=f"[GRC] Evidenza scaduta: {instance.control.external_id}",
        body=(
            f"Le evidenze del controllo {instance.control.external_id} "
            "sono scadute.\n\n"
            f"Plant:     {instance.plant.name}\n"
            f"Controllo: {instance.control.get_title('it')}\n\n"
            "Caricare nuova evidenza per mantenere stato Compliant."
        ),
        recipients=recipients,
    )


def notify_document_approval_needed(document, recipients: list[str]):
    send_grc_email(
        subject=f"[GRC] Approvazione richiesta: {document.title}",
        body=(
            "Un documento richiede la tua approvazione.\n\n"
            f"Titolo:  {document.title}\n"
            f"Tipo:    {document.document_type}\n"
            f"Plant:   {document.plant.name if document.plant else '—'}\n\n"
            "Accedi al sistema per approvare o richiedere modifiche."
        ),
        recipients=recipients,
    )


def notify_document_review_needed(document, recipients: list[str]):
    """
    Notifica che un documento è stato inviato in revisione.
    """
    send_grc_email(
        subject=f"[GRC] Revisione richiesta: {document.title}",
        body=(
            "Un documento è stato inviato in revisione.\n\n"
            f"Titolo:  {document.title}\n"
            f"Tipo:    {document.document_type}\n"
            f"Plant:   {document.plant.name if document.plant else '—'}\n\n"
            "Accedi al sistema per revisionare il contenuto."
        ),
        recipients=recipients,
    )


def notify_kpi_alert(kpi_def, plant, snapshot, recipients: list[str]):
    """
    Alert per un KPI operativo che ha superato la soglia (warning/critical).
    Segue il pattern degli altri notify_*: contenuto qui, destinatari risolti
    dal chiamante (apps.tasks.services._send_kpi_alert).
    """
    status_label = {"warning": "⚠️ Warning", "critical": "🔴 Critico"}.get(
        snapshot.status, snapshot.status
    )
    plant_label = plant.name if plant else "Tutti i plant (globale)"
    value_label = (
        f"{snapshot.value} {kpi_def.unit}".strip()
        if snapshot.value is not None
        else "n/d"
    )
    send_grc_email(
        subject=f"[GRC] {status_label} KPI: {kpi_def.name}",
        body=(
            "Un KPI operativo ha superato la soglia configurata.\n\n"
            f"KPI:        {kpi_def.name} ({kpi_def.kpi_code})\n"
            f"Stato:      {status_label}\n"
            f"Valore:     {value_label}\n"
            f"Settimana:  {snapshot.week_start}\n"
            f"Plant:      {plant_label}\n\n"
            "Accedi alla dashboard KPI operativi per analizzare il trend."
        ),
        recipients=recipients,
    )


def notify_document_approved_broadcast(document, recipients: list[str]):
    """
    Notifica a tutti i membri del sito che un nuovo documento è stato approvato.
    """
    send_grc_email(
        subject=f"[GRC] Nuovo documento approvato: {document.title}",
        body=(
            "Un nuovo documento è stato approvato ed è ora in vigore.\n\n"
            f"Titolo:   {document.title}\n"
            f"Tipo:     {document.document_type}\n"
            f"Plant:    {document.plant.name if document.plant else '—'}\n"
            f"Valido da: {document.approved_at}\n\n"
            "Accedi a Documenti & Evidenze per consultare l'ultima versione."
        ),
        recipients=recipients,
    )


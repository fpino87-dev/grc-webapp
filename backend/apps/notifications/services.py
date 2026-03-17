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
) -> bool:
    """
    Invia email GRC usando config da DB.
    Restituisce True se inviata, False se fallita.
    """
    if not recipients:
        return False

    from .models import EmailConfiguration

    config = EmailConfiguration.get_active()
    from_email = config.from_email if config else "GRC Platform <noreply@grc.local>"

    try:
        connection = _get_connection()
        msg = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=from_email,
            to=recipients,
            connection=connection,
        )
        if html_body:
            msg.attach_alternative(html_body, "text/html")
        msg.send()
        logger.info("Email inviata a %s: %s", recipients, subject)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Errore invio email a %s: %s", recipients, exc)
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


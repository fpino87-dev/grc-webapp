import datetime

from django.utils import timezone

from .models import Supplier, SupplierQuestionnaire


def get_expiring_contracts(days: int = 60):
    """Return suppliers whose evaluation_date expires within the given number of days."""
    today = timezone.now().date()
    deadline = today + datetime.timedelta(days=days)
    return Supplier.objects.filter(
        status="attivo",
        evaluation_date__isnull=False,
        evaluation_date__lte=deadline,
        evaluation_date__gte=today,
    )


def get_high_risk_suppliers():
    """Return suppliers with risk_level alto or critico."""
    return Supplier.objects.filter(risk_level__in=["alto", "critico"], status="attivo")


def complete_assessment(
    assessment,
    user,
    score_overall=None,
    score_governance=None,
    score_security=None,
    score_bcp=None,
    findings: str = "",
    next_assessment_months: int = 12,
):
    from core.audit import log_action
    from apps.compliance_schedule.services import get_due_date

    assessment.status = "completato"
    assessment.assessed_by = user
    assessment.assessment_date = timezone.now().date()
    assessment.score = score_overall
    assessment.score_overall = score_overall
    assessment.score_governance = score_governance
    assessment.score_security = score_security
    assessment.score_bcp = score_bcp
    assessment.findings = findings
    assessment.next_assessment_date = get_due_date(
        "supplier_assessment",
        plant=assessment.supplier.plants.first(),
    )
    assessment.save()

    if score_overall is not None:
        supplier = assessment.supplier
        if score_overall >= 75:
            supplier.risk_level = "basso"
        elif score_overall >= 50:
            supplier.risk_level = "medio"
        else:
            supplier.risk_level = "alto"
        supplier.save(update_fields=["risk_level", "updated_at"])

    log_action(
        user=user,
        action_code="supplier.assessment.completed",
        level="L2",
        entity=assessment,
        payload={
            "score_overall": score_overall,
            "risk_level": assessment.computed_risk_level,
        },
    )

    try:
        from apps.notifications.resolver import fire_notification
        fire_notification(
            "supplier_assessment",
            plant=assessment.supplier.plants.first(),
            context={"assessment": assessment},
        )
    except Exception:
        pass
    return assessment


def approve_assessment(assessment, user, notes: str = ""):
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _
    from core.audit import log_action

    if assessment.status != "completato":
        raise ValidationError(_("Solo assessment completati possono essere approvati."))

    assessment.status = "approvato"
    assessment.reviewed_by = user
    assessment.reviewed_at = timezone.now()
    assessment.review_notes = notes
    assessment.save(
        update_fields=[
            "status", "reviewed_by", "reviewed_at", "review_notes", "updated_at",
        ]
    )

    log_action(
        user=user,
        action_code="supplier.assessment.approved",
        level="L1",
        entity=assessment,
        payload={"notes": notes[:100]},
    )
    return assessment


def reject_assessment(assessment, user, notes: str = ""):
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _
    from core.audit import log_action

    if not notes or len(notes.strip()) < 10:
        raise ValidationError(_("Motivazione rifiuto obbligatoria (min 10 caratteri)."))

    assessment.status = "rifiutato"
    assessment.reviewed_by = user
    assessment.reviewed_at = timezone.now()
    assessment.review_notes = notes
    assessment.save(
        update_fields=[
            "status", "reviewed_by", "reviewed_at", "review_notes", "updated_at",
        ]
    )

    log_action(
        user=user,
        action_code="supplier.assessment.rejected",
        level="L1",
        entity=assessment,
        payload={"notes": notes[:200]},
    )
    return assessment


# ── Questionnaire services ──────────────────────────────────────────────────


def _build_email_body(template, supplier) -> tuple[str, str]:
    """Interpolate template variables. Returns (subject, body)."""
    subject = template.subject.replace("{supplier_name}", supplier.name)
    body = template.body.replace("{supplier_name}", supplier.name).replace(
        "{questionnaire_link}", template.form_url
    )
    return subject, body


def send_questionnaire(supplier, template, user) -> "SupplierQuestionnaire":
    """
    First send of a questionnaire to a supplier.
    Creates SupplierQuestionnaire record and sends email.
    """
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _
    from core.audit import log_action
    from apps.notifications.services import send_grc_email

    if not supplier.email:
        raise ValidationError(_("Nessun indirizzo email configurato per questo fornitore."))

    now = timezone.now()
    subject, body = _build_email_body(template, supplier)

    questionnaire = SupplierQuestionnaire(
        supplier=supplier,
        template=template,
        subject_snapshot=subject,
        body_snapshot=body,
        form_url_snapshot=template.form_url,
        sent_at=now,
        last_sent_at=now,
        sent_to=supplier.email,
        sent_by=user,
        send_count=1,
        status="inviato",
        created_by=user,
    )
    questionnaire.save()

    send_grc_email(
        subject=subject,
        body=body,
        recipients=[supplier.email],
    )

    log_action(
        user=user,
        action_code="supplier.questionnaire.sent",
        level="L2",
        entity=questionnaire,
        payload={
            "supplier": supplier.name,
            "sent_to": supplier.email,
            "template": template.name,
            "send_count": 1,
        },
    )
    return questionnaire


def resend_questionnaire(questionnaire, user) -> "SupplierQuestionnaire":
    """
    Resend an existing questionnaire (follow-up). Increments send_count.
    """
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _
    from core.audit import log_action
    from apps.notifications.services import send_grc_email

    if questionnaire.status == "risposto":
        raise ValidationError(_("Il questionario ha già ricevuto risposta."))

    now = timezone.now()
    questionnaire.send_count += 1
    questionnaire.last_sent_at = now
    if questionnaire.send_count >= 3:
        questionnaire.status = "inviato"  # keep as inviato but send_count signals 3rd strike
    questionnaire.save(update_fields=["send_count", "last_sent_at", "status", "updated_at"])

    send_grc_email(
        subject=questionnaire.subject_snapshot,
        body=questionnaire.body_snapshot,
        recipients=[questionnaire.sent_to],
    )

    log_action(
        user=user,
        action_code="supplier.questionnaire.resent",
        level="L2",
        entity=questionnaire,
        payload={
            "supplier": questionnaire.supplier.name,
            "sent_to": questionnaire.sent_to,
            "send_count": questionnaire.send_count,
        },
    )
    return questionnaire


def register_evaluation(questionnaire, evaluation_date, risk_result, user, notes: str = "") -> "SupplierQuestionnaire":
    """
    Record the received evaluation: sets evaluation_date, risk_result, expires_at (+1 year).
    Updates supplier.risk_level and supplier.evaluation_date.
    """
    from core.audit import log_action

    expires_at = evaluation_date + datetime.timedelta(days=365)

    questionnaire.evaluation_date = evaluation_date
    questionnaire.risk_result = risk_result
    questionnaire.status = "risposto"
    questionnaire.expires_at = expires_at
    if notes:
        questionnaire.notes = notes
    questionnaire.save(
        update_fields=[
            "evaluation_date", "risk_result", "status", "expires_at", "notes", "updated_at"
        ]
    )

    # Update supplier
    supplier = questionnaire.supplier
    supplier.risk_level = risk_result
    supplier.evaluation_date = evaluation_date
    supplier.save(update_fields=["risk_level", "evaluation_date", "updated_at"])

    log_action(
        user=user,
        action_code="supplier.questionnaire.evaluated",
        level="L2",
        entity=questionnaire,
        payload={
            "supplier": supplier.name,
            "evaluation_date": str(evaluation_date),
            "risk_result": risk_result,
            "expires_at": str(expires_at),
        },
    )
    return questionnaire


def check_questionnaire_followups():
    """
    Check questionnaires awaiting response for > 7 days since last send.
    Notifies the operator who sent (sent_by) via email.
    """
    from apps.notifications.services import send_grc_email

    today = timezone.now().date()
    threshold = timezone.now() - datetime.timedelta(days=7)

    pending = SupplierQuestionnaire.objects.filter(
        status="inviato",
        evaluation_date__isnull=True,
        last_sent_at__lt=threshold,
        deleted_at__isnull=True,
    ).select_related("supplier", "sent_by")

    for q in pending:
        days_waiting = (today - q.last_sent_at.date()).days
        operator_email = q.sent_by.email if q.sent_by and q.sent_by.email else None
        if not operator_email:
            continue

        if q.send_count >= 3:
            subject = f"[GRC] \U0001f534 Fornitore {q.supplier.name} — 3 tentativi senza risposta"
            body = (
                f"Il questionario inviato al fornitore {q.supplier.name} ({q.sent_to}) "
                f"non ha ricevuto risposta dopo {q.send_count} invii ({days_waiting} giorni dall'ultimo).\n\n"
                "\u26a0\ufe0f Azione richiesta: contattare il fornitore direttamente (telefono/presenza).\n\n"
                "Accedi al modulo Fornitori per aggiornare lo stato."
            )
        else:
            next_count = q.send_count + 1
            subject = f"[GRC] Follow-up questionario — {q.supplier.name} ({days_waiting}gg senza risposta)"
            body = (
                f"Il questionario inviato al fornitore {q.supplier.name} ({q.sent_to}) "
                f"non ha ricevuto risposta da {days_waiting} giorni.\n\n"
                f"Invio numero: {q.send_count} — prossimo previsto: {next_count}\u00b0\n\n"
                "Accedi al modulo Fornitori per inviare il promemoria."
            )

        send_grc_email(subject=subject, body=body, recipients=[operator_email])

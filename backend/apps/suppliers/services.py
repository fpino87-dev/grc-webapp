from django.utils import timezone

from .models import Supplier


def get_expiring_contracts(days: int = 60):
    """Return suppliers whose contract expires within the given number of days."""
    import datetime

    today = timezone.now().date()
    deadline = today + datetime.timedelta(days=days)
    return Supplier.objects.filter(
        status="attivo",
        contract_expiry__isnull=False,
        contract_expiry__lte=deadline,
        contract_expiry__gte=today,
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

    # Aggiorna risk level sul Supplier
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

    # Notifica al risk manager se completato
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
            "status",
            "reviewed_by",
            "reviewed_at",
            "review_notes",
            "updated_at",
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
            "status",
            "reviewed_by",
            "reviewed_at",
            "review_notes",
            "updated_at",
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

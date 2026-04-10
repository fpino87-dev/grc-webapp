from celery import shared_task
from django.utils import timezone

from core.audit import log_action
from apps.auth_grc.models import GrcRole
from apps.tasks.services import create_task


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def check_expiring_risk_acceptances():
    """
    Giornaliero: controlla le accettazioni formali di rischio in scadenza.

    - Entro 30 giorni dalla scadenza: setta needs_revaluation=True e crea
      Task per il risk_manager del plant (rivalutazione preventiva).
    - Già scadute (expiry < oggi): stessa logica, priorità alta.

    Evita di creare task duplicati sullo stesso rischio se il flag
    needs_revaluation è già True (già processato in precedenza).
    """
    from .models import RiskAssessment

    today = timezone.now().date()
    warning_threshold = today + timezone.timedelta(days=30)

    User = __import__("django.contrib.auth", fromlist=["get_user_model"]).get_user_model()
    system_user = User.objects.filter(is_superuser=True).first()

    # Rischi con accettazione formale che scade entro 30 giorni (o già scaduta)
    # e che non sono già stati marcati per rivalutazione
    expiring = RiskAssessment.objects.filter(
        deleted_at__isnull=True,
        risk_accepted_formally=True,
        risk_acceptance_expiry__isnull=False,
        risk_acceptance_expiry__lte=warning_threshold,
        needs_revaluation=False,
    ).select_related("plant", "owner")

    count = 0
    for risk in expiring:
        already_expired = risk.risk_acceptance_expiry < today
        days_left = (risk.risk_acceptance_expiry - today).days

        # Setta flag rivalutazione
        risk.needs_revaluation = True
        risk.needs_revaluation_since = today
        risk.save(update_fields=["needs_revaluation", "needs_revaluation_since", "updated_at"])

        if system_user:
            log_action(
                user=system_user,
                action_code="risk.acceptance.expiring",
                level="L2",
                entity=risk,
                payload={
                    "id": str(risk.id),
                    "risk_name": risk.name,
                    "expiry": str(risk.risk_acceptance_expiry),
                    "days_left": days_left,
                    "already_expired": already_expired,
                },
            )

        if already_expired:
            title = f"Accettazione rischio SCADUTA — rivalutazione obbligatoria: {risk.name}"
            description = (
                f"L'accettazione formale del rischio '{risk.name}' è scaduta il "
                f"{risk.risk_acceptance_expiry}. "
                "Rivaluta il rischio residuo e rinnova o modifica la strategia di trattamento."
            )
            priority = "alta"
            due_days = 7
        else:
            title = f"Accettazione rischio in scadenza ({days_left}gg) — {risk.name}"
            description = (
                f"L'accettazione formale del rischio '{risk.name}' scade il "
                f"{risk.risk_acceptance_expiry} ({days_left} giorni). "
                "Rivaluta il rischio residuo e rinnova l'accettazione se ancora appropriata."
            )
            priority = "media" if days_left > 14 else "alta"
            due_days = max(1, days_left - 7)

        create_task(
            plant=risk.plant,
            title=title,
            description=description,
            priority=priority,
            source_module="M06",
            source_id=risk.pk,
            due_date=today + timezone.timedelta(days=due_days),
            assign_type="role",
            assign_value=GrcRole.RISK_MANAGER,
        )

        count += 1

    return f"check_expiring_risk_acceptances: {count} rischi marcati per rivalutazione"

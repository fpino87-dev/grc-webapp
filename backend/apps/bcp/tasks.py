from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model

from core.audit import log_action
from apps.bcp.models import BcpPlan
from apps.auth_grc.models import GrcRole
from apps.tasks.services import create_task


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def check_expired_bcp_plans():
    """
    Alla scadenza di un BCP approvato:
    - declassa il piano a `bozza` (approvazione scaduta)
    - crea Task per `risk_manager` (ritest + riapprovazione)
    - crea Task di informazione per `compliance_officer` (usato come "ciso di plant")
    """
    User = get_user_model()
    system_user = User.objects.filter(is_superuser=True).first()
    today = timezone.now().date()

    plans = BcpPlan.objects.filter(
        deleted_at__isnull=True,
        status="approvato",
        next_test_date__isnull=False,
    ).filter(next_test_date__lte=today)

    for plan in plans.select_related("plant"):
        # 1) Degrado approvazione
        plan.status = "bozza"
        plan.save(update_fields=["status", "updated_at"])

        if system_user:
            log_action(
                user=system_user,
                action_code="bcp.plan.approval_expired",
                level="L2",
                entity=plan,
                payload={
                    "id": str(plan.id),
                    "title": plan.title,
                    "expired_on": str(today),
                },
            )

        # 2) Task per ritest/riapprovazione (risk_manager)
        create_task(
            plant=plan.plant,
            title=f"Ritest BCP e riapprovazione — {plan.title}",
            description=(
                "L'approvazione del piano BCP è scaduta. "
                "Esegui il ritest e poi richiedi la riapprovazione."
            ),
            priority="alta",
            source_module="M16",
            source_id=plan.pk,
            due_date=today + timezone.timedelta(days=15),
            assign_type="role",
            assign_value=GrcRole.RISK_MANAGER,
        )

        # 3) Informazione CISO (plant) tramite task per compliance_officer
        create_task(
            plant=plan.plant,
            title=f"Approvazione BCP richiesta — {plan.title}",
            description="Ti è stato notificato che il piano BCP richiede riapprovazione dopo scadenza.",
            priority="media",
            source_module="M16",
            source_id=plan.pk,
            due_date=today + timezone.timedelta(days=3),
            assign_type="role",
            assign_value=GrcRole.COMPLIANCE_OFFICER,
        )

    return f"check_expired_bcp_plans: {plans.count()} piani aggiornati"


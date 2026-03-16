from celery import shared_task
from django.utils import timezone


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def check_expired_evidences():
    """
    Eseguito ogni notte alle 02:00.
    Per ogni ControlInstance compliant con tutte le evidenze scadute:
    - degrada a "parziale"
    - crea task al control owner
    """
    from .models import ControlInstance
    from apps.tasks.services import create_task
    from core.audit import log_action
    from django.contrib.auth import get_user_model

    User = get_user_model()
    today = timezone.now().date()
    system_user = User.objects.filter(is_superuser=True).first()

    instances = ControlInstance.objects.filter(
        status="compliant",
        deleted_at__isnull=True,
    ).prefetch_related("evidences")

    degraded = 0
    for instance in instances:
        valid = instance.evidences.filter(
            valid_until__gte=today,
            deleted_at__isnull=True,
        ).exists()

        if not valid:
            instance.status = "parziale"
            instance.save(update_fields=["status", "updated_at"])
            degraded += 1

            if instance.owner:
                create_task(
                    plant=instance.plant,
                    title=f"Evidenza scaduta — {instance.control.external_id}",
                    description=(
                        f"Il controllo {instance.control.external_id} era Compliant "
                        f"ma tutte le evidenze collegate sono scadute. "
                        f"Carica una nuova evidenza per ripristinare lo stato."
                    ),
                    priority="alta",
                    source_module="M03",
                    source_id=instance.pk,
                    due_date=today + timezone.timedelta(days=15),
                    assign_type="user",
                    assign_value=str(instance.owner.pk),
                    control_instance=instance,
                )

            if system_user:
                log_action(
                    user=system_user,
                    action_code="control.evidence_expired",
                    level="L2",
                    entity=instance,
                    payload={"degraded_to": "parziale", "date": str(today)},
                )

    return f"check_expired_evidences: {degraded} controlli degradati"

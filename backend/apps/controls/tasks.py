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
    Per ogni ControlInstance compliant con requisiti non soddisfatti
    (evidenze scadute o mancanti, documenti mancanti):
    - degrada a "parziale"
    - crea task al control owner con titolo appropriato:
        * "Evidenza scaduta" se ci sono evidenze con valid_until < oggi
        * "Nessuna evidenza valida" se i requisiti non sono soddisfatti ma senza scadute
    I controlli che richiedono solo documenti (policy/procedure) non vengono
    degradati se i documenti obbligatori sono presenti.
    """
    from .models import ControlInstance
    from .services import check_evidence_requirements
    from apps.tasks.services import create_task
    from core.audit import log_action
    from django.contrib.auth import get_user_model

    User = get_user_model()
    today = timezone.now().date()
    system_user = User.objects.filter(is_superuser=True).first()

    from django.db.models import Exists, OuterRef
    from apps.plants.models import PlantFramework

    # Salta istanze il cui plant non ha più il framework associato (es. dopo rimozione PlantFramework)
    active_pf = PlantFramework.objects.filter(
        plant=OuterRef("plant"),
        framework=OuterRef("control__framework"),
    )

    instances = ControlInstance.objects.filter(
        status="compliant",
        deleted_at__isnull=True,
    ).annotate(
        has_active_pf=Exists(active_pf),
    ).filter(
        has_active_pf=True,
    ).select_related("control", "plant", "owner").prefetch_related("evidences", "documents")

    degraded = 0
    for instance in instances:
        req_check = check_evidence_requirements(instance)

        if req_check["satisfied"]:
            continue

        # Distingui: evidenze scadute vs requisiti mai soddisfatti
        has_expired = bool(req_check["expired_evidences"])
        if has_expired:
            task_title = f"Evidenza scaduta — {instance.control.external_id}"
            task_description = (
                f"Il controllo {instance.control.external_id} era Compliant "
                f"ma le evidenze collegate sono scadute. "
                f"Carica una nuova evidenza per ripristinare lo stato."
            )
        else:
            task_title = f"Nessuna evidenza valida — {instance.control.external_id}"
            task_description = (
                f"Il controllo {instance.control.external_id} era Compliant "
                f"ma non ha evidenze o documenti validi collegati. "
                f"Collega un'evidenza o un documento approvato per ripristinare lo stato."
            )

        instance.status = "parziale"
        instance.save(update_fields=["status", "updated_at"])
        degraded += 1

        if instance.owner:
            create_task(
                plant=instance.plant,
                title=task_title,
                description=task_description,
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
                payload={
                    "degraded_to": "parziale",
                    "date": str(today),
                    "has_expired_evidences": has_expired,
                },
            )

        try:
            from apps.notifications.resolver import fire_notification

            fire_notification(
                "evidence_expired",
                plant=instance.plant,
                context={"instance": instance},
            )
        except Exception:
            pass

    return f"check_expired_evidences: {degraded} controlli degradati"

from celery import shared_task


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, default_retry_delay=60)
def notify_blocked_pdca_task(self):
    from django.utils import timezone

    from apps.notifications.resolver import fire_notification
    from apps.pdca.models import PdcaCycle

    threshold = timezone.now() - timezone.timedelta(days=30)
    blocked = (
        PdcaCycle.objects.filter(
            fase_corrente="plan",
            created_at__lt=threshold,
            deleted_at__isnull=True,
        ).select_related("plant")
    )

    for cycle in blocked:
        fire_notification(
            "pdca_blocked",
            plant=cycle.plant,
            context={"cycle": cycle},
        )


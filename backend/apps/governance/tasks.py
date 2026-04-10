from celery import shared_task


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, default_retry_delay=60)
def notify_expiring_roles_task(self):
    from django.utils import timezone

    from apps.governance.services import get_expiring_delegations
    from apps.notifications.resolver import fire_notification

    delegations = get_expiring_delegations(days=30)
    for assignment in delegations:
        days_left = (assignment.valid_until - timezone.now().date()).days
        fire_notification(
            "role_expiring",
            context={"assignment": assignment, "days_left": days_left},
        )


from celery import shared_task
from django.utils import timezone


@shared_task(
    name="apps.assets.tasks.check_unrevalued_changes",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def check_unrevalued_changes():
    """
    Ogni lunedì: verifica asset con change non rivalutati da > 14gg.
    Crea task di reminder al plant manager.
    """
    from .models import Asset
    from apps.tasks.services import create_task

    threshold = timezone.now().date() - timezone.timedelta(days=14)
    assets = Asset.objects.filter(
        needs_revaluation=True,
        needs_revaluation_since__lte=threshold,
        deleted_at__isnull=True,
    ).select_related("plant")

    count = 0
    for asset in assets:
        create_task(
            plant=asset.plant,
            title=f"Rivalutazione in sospeso: {asset.name}",
            description=(
                f"L'asset '{asset.name}' ha un change registrato "
                f"({asset.last_change_ref}) dal "
                f"{asset.needs_revaluation_since} "
                f"ma non è ancora stato rivalutato.\n\n"
                f"Change: {asset.last_change_desc}\n"
                f"Ticket: {asset.change_portal_url or '—'}\n\n"
                f"Verificare controlli e risk assessment collegati."
            ),
            priority="alta",
            source_module="M04",
            source_id=asset.pk,
            due_date=timezone.now().date() + timezone.timedelta(days=7),
            assign_type="role",
            assign_value="plant_manager",
        )
        count += 1

    return f"check_unrevalued_changes: {count} reminder creati"

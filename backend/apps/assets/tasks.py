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


@shared_task(
    name="apps.assets.tasks.check_software_eos",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def check_software_eos():
    """
    Ogni lunedì: verifica asset SW con end_of_support in scadenza.
    - entro 90 giorni → task priorità "media" (avviso pianificazione)
    - entro 30 giorni → task priorità "alta" (azione urgente)
    Non ricrea task se ne esiste già uno aperto per lo stesso asset.
    """
    from .models import AssetSW
    from apps.tasks.models import Task
    from apps.tasks.services import create_task

    today = timezone.now().date()
    threshold_warn = today + timezone.timedelta(days=90)
    threshold_urgent = today + timezone.timedelta(days=30)

    assets = AssetSW.objects.filter(
        deleted_at__isnull=True,
        end_of_support__isnull=False,
        end_of_support__lte=threshold_warn,
        end_of_support__gte=today,
    ).select_related("plant", "owner")

    count = 0
    for asset in assets:
        already_open = Task.objects.filter(
            source_module="M04",
            source_id=asset.pk,
            title__icontains="fine supporto",
            status__in=["aperto", "in_corso"],
            deleted_at__isnull=True,
        ).exists()
        if already_open:
            continue

        days_left = (asset.end_of_support - today).days
        if days_left <= threshold_urgent.toordinal() - today.toordinal():
            priority = "alta"
        else:
            priority = "media"

        create_task(
            plant=asset.plant,
            title=f"Fine supporto software: {asset.name}",
            description=(
                f"Il software '{asset.name}' (vendor: {asset.vendor or '—'}, "
                f"versione: {asset.version or '—'}) raggiunge la data di fine supporto "
                f"il {asset.end_of_support}.\n\n"
                f"Azioni suggerite:\n"
                f"- Verificare disponibilità aggiornamento/versione successiva\n"
                f"- Valutare alternativa se EOS non rinnovabile\n"
                f"- Aggiornare il risk assessment associato\n"
                f"Rif. esterno: {asset.external_ref or '—'}"
            ),
            priority=priority,
            source_module="M04",
            source_id=asset.pk,
            due_date=asset.end_of_support,
            assign_type="role",
            assign_value="plant_manager",
        )
        count += 1

    return f"check_software_eos: {count} task creati"

from celery import shared_task
from django.db import models
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

    threshold = timezone.localdate() - timezone.timedelta(days=14)
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
            due_date=timezone.localdate() + timezone.timedelta(days=7),
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

    today = timezone.localdate()
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


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def check_maintenance_due():
    """
    Eseguito ogni notte. Manutenzione periodica di apparati e impianti.

    - completa `next_maintenance_date` sugli asset che hanno una cadenza ma non
      ancora una scadenza (contando dall'ultima manutenzione registrata o, se
      non c'è, da oggi: meglio far partire l'orologio che lasciare l'asset
      fuori dal piano per sempre);
    - dentro la finestra di preavviso della policy apre un task all'owner
      dell'asset — o al plant manager se l'asset non ha un owner — e segna la
      scadenza come già segnalata, così il giro successivo non duplica.

    Registrare la manutenzione (`services.record_maintenance`) sposta avanti la
    scadenza e l'asset torna da segnalare al momento giusto.
    """
    from apps.plants.services import plant_today
    from apps.tasks.services import create_task
    from core.audit import log_action
    from core.periodic import due_status
    from django.contrib.auth import get_user_model

    from .models import Asset
    from .services import apply_maintenance_schedule

    User = get_user_model()
    system_user = User.objects.filter(is_superuser=True).first()

    programmed = Asset.objects.filter(
        deleted_at__isnull=True, maintenance_frequency_months__isnull=False
    ).select_related("plant", "owner", "maintainer_supplier")

    scheduled = 0
    for asset in programmed.filter(next_maintenance_date__isnull=True):
        if apply_maintenance_schedule(asset, base=asset.last_maintenance_date) is not None:
            scheduled += 1

    alerted = 0
    for asset in programmed.filter(next_maintenance_date__isnull=False).exclude(
        maintenance_alert_for=models.F("next_maintenance_date")
    ):
        today = plant_today(asset.plant)
        to_alert, days_left, already_due = due_status(
            asset.plant, "asset_maintenance", asset.next_maintenance_date, today
        )
        if not to_alert:
            continue

        asset.maintenance_alert_for = asset.next_maintenance_date
        asset.save(update_fields=["maintenance_alert_for", "updated_at"])
        alerted += 1

        maintainer = (
            asset.maintainer_supplier.name if asset.maintainer_supplier else "interno"
        )
        if already_due:
            title = f"Manutenzione SCADUTA — {asset.name}"
            description = (
                f"La manutenzione programmata di '{asset.name}' era attesa entro il "
                f"{asset.next_maintenance_date} ({abs(days_left)} giorni fa). "
                f"Manutentore: {maintainer}."
            )
            priority, due_days = "alta", 7
        else:
            title = f"Manutenzione in scadenza ({days_left}gg) — {asset.name}"
            description = (
                f"'{asset.name}' va manutenuto entro il {asset.next_maintenance_date} "
                f"({days_left} giorni). Manutentore: {maintainer}."
            )
            priority, due_days = ("media" if days_left > 14 else "alta"), max(1, days_left)

        assign_type, assign_value = (
            ("user", str(asset.owner.pk)) if asset.owner else ("role", "plant_manager")
        )
        create_task(
            plant=asset.plant,
            title=title,
            description=description,
            priority=priority,
            source_module="M04",
            source_id=asset.pk,
            due_date=today + timezone.timedelta(days=due_days),
            assign_type=assign_type,
            assign_value=assign_value,
        )

        if system_user:
            log_action(
                user=system_user,
                action_code="asset.maintenance_due",
                level="L2",
                entity=asset,
                payload={
                    "id": str(asset.pk),
                    "name": asset.name,
                    "next_maintenance_date": str(asset.next_maintenance_date),
                    "days_left": days_left,
                    "already_due": already_due,
                },
            )

    return (
        f"check_maintenance_due: {alerted} manutenzioni segnalate, "
        f"{scheduled} scadenze pianificate"
    )

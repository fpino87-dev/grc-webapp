import datetime
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, retry_backoff=True)
def generate_scheduled_checklists(self):
    """
    Ogni giorno alle 07:00:
    1) marca come 'overdue' i run pending/in_progress con due_date passata;
    2) genera i ChecklistRun di competenza per ogni template attivo, in base
       alla frequenza e al giorno configurato, evitando duplicati su
       (template, plant, scadenza);
    3) valuta la soglia PDCA: 3 run consecutivi incompleti aprono un ciclo M11.

    I template ad_hoc non vengono mai generati automaticamente: si avviano a
    mano dalla UI (services.start_manual_run).
    """
    from apps.plants.models import Plant

    from . import services
    from .models import ChecklistRun, ChecklistTemplate

    today = timezone.localdate()

    # 1) Scaduti: i run non conclusi con scadenza passata diventano overdue.
    overdue_qs = ChecklistRun.objects.filter(
        status__in=["pending", "in_progress"], due_date__lt=today
    )
    overdue_count = overdue_qs.update(status="overdue", updated_at=timezone.now())

    # 2) Generazione dei run di competenza (vedi services.checklist_due_date_for:
    #    giorno scelto per giornaliera/settimanale/mensile, scadenza a fine
    #    periodo, recupero del periodo ancora scoperto).
    created_count = 0
    templates = (
        ChecklistTemplate.objects.filter(is_active=True)
        .select_related("plant")
        .prefetch_related("items")
    )
    for template in templates:
        due_date = services.checklist_due_date_for(template, today)
        if due_date is None:
            continue
        if template.plant_id:
            target_plants = [template.plant]
        else:
            # plant null → template valido per tutti i plant attivi
            target_plants = list(Plant.objects.filter(status="attivo"))
        for plant in target_plants:
            already = ChecklistRun.objects.filter(
                template=template, plant=plant, due_date=due_date
            ).exists()
            services.create_run_for_template(template, plant, due_date)
            if not already:
                created_count += 1

    # 3) Soglia PDCA su run consecutivi incompleti.
    pdca_count = 0
    for template in templates:
        cycle = services.evaluate_checklist_pdca_threshold(template)
        if cycle is not None:
            pdca_count += 1

    return (
        f"generate_scheduled_checklists: {created_count} run creati, "
        f"{overdue_count} scaduti, {pdca_count} PDCA aperti"
    )


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, retry_backoff=True)
def compute_operational_kpis(self):
    """
    Ogni lunedì alle 06:30. Calcola gli snapshot settimanali dei KPI operativi
    per la settimana APPENA CONCLUSA (lunedì→domenica precedenti): quando il
    task gira il lunedì mattina la settimana corrente non contiene ancora run,
    quindi misurarla darebbe sempre no_data. Per ogni KPIDefinition attiva con
    source=checklist (aggregazione run) o source=internal (connettore che legge
    direttamente i dati dei moduli M03/M04/M07/M09/M11/M14/M15/M17), su tutti i
    plant pertinenti: il sito della definizione se valorizzato, altrimenti
    tutti i plant attivi tranne quelli che hanno una propria definizione dello
    stesso kpi_code (che ha la precedenza sulla globale).
    Invia alert M19 quando uno status peggiora oltre soglia.
    """
    from apps.plants.models import Plant

    from . import services
    from .models import KPIDefinition

    # Settimana conclusa: il lunedì di 7 giorni fa.
    week_start = services._monday_of(
        timezone.localdate() - datetime.timedelta(days=7)
    )
    snapshot_count = 0
    alert_count = 0

    kpis = (
        KPIDefinition.objects.filter(
            is_active=True, source__in=["checklist", "internal"]
        )
        .select_related("plant", "checklist_template")
    )
    active_plants = list(Plant.objects.filter(status="attivo"))
    for kpi_def in kpis:
        if kpi_def.plant_id:
            target_plants = [kpi_def.plant]
        else:
            # Definizione globale: vale solo per i siti che non hanno una
            # propria definizione dello stesso kpi_code. Chi ne ha una decide
            # soglie e attivazione per conto suo (anche disattivandola), e
            # misurare due volte lo stesso KPI sullo stesso sito produrrebbe
            # snapshot doppi in dashboard.
            overridden = set(
                KPIDefinition.objects.filter(
                    kpi_code=kpi_def.kpi_code, plant__isnull=False
                ).values_list("plant_id", flat=True)
            )
            target_plants = [p for p in active_plants if p.id not in overridden]
        for plant in target_plants:
            snapshot = services.compute_and_store_kpi_snapshot(
                kpi_def, plant, week_start
            )
            snapshot_count += 1
            if getattr(snapshot, "_alert_sent", False):
                alert_count += 1

    return (
        f"compute_operational_kpis: {snapshot_count} snapshot, "
        f"{alert_count} alert inviati (week_start={week_start})"
    )


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, retry_backoff=True)
def roll_recurring_tasks(self):
    """
    Ogni notte: i task ricorrenti la cui scadenza è passata senza che siano
    stati chiusi generano comunque l'occorrenza successiva.

    Prima la ricorrenza si propagava SOLO alla chiusura (`complete_task`): un
    task ricorrente scaduto e mai completato interrompeva la serie in
    silenzio, senza alcun segnale. Su una verifica annuale ci si sarebbe
    accorti del buco l'anno dopo, in audit.

    Il task mancato NON viene chiuso né modificato: resta aperto come traccia
    del periodo saltato, e accanto compare l'occorrenza del periodo nuovo.
    """
    from django.db.models import Exists, OuterRef

    from . import services
    from .models import Task

    today = timezone.localdate()
    # Un task che ha già un figlio ha già propagato la ricorrenza.
    has_child = Task.objects.filter(parent_task=OuterRef("pk"))
    pending = (
        Task.objects.filter(
            recurrence__in=Task.RECURRENCE_STEPS.keys(),
            due_date__lt=today,
            status__in=["aperto", "in_corso", "scaduto"],
        )
        .annotate(already_rolled=Exists(has_child))
        .filter(already_rolled=False)
        .select_related("plant")
    )

    created = 0
    for task in pending:
        note = (
            f"Occorrenza generata automaticamente: la precedente, in scadenza "
            f"il {task.due_date}, non è stata completata."
        )
        if services._spawn_next_recurrence(task, note=note) is not None:
            created += 1

    return f"roll_recurring_tasks: {created} occorrenze ricorrenti generate"

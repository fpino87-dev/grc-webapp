import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, retry_backoff=True)
def generate_scheduled_checklists(self):
    """
    Ogni giorno alle 07:00:
    1) marca come 'overdue' i run pending/in_progress con due_date passata;
    2) genera i ChecklistRun di oggi per ogni template attivo, in base alla
       frequenza, evitando duplicati su (template, plant, data odierna);
    3) valuta la soglia PDCA: 3 run consecutivi incompleti aprono un ciclo M11.

    I template ad_hoc non vengono mai generati automaticamente.
    """
    from apps.plants.models import Plant

    from . import services
    from .models import ChecklistRun, ChecklistTemplate

    today = timezone.now().date()

    # 1) Scaduti: i run non conclusi con scadenza passata diventano overdue.
    overdue_qs = ChecklistRun.objects.filter(
        status__in=["pending", "in_progress"], due_date__lt=today
    )
    overdue_count = overdue_qs.update(status="overdue", updated_at=timezone.now())

    # 2) Generazione run odierni in base alla frequenza.
    def _is_due_today(frequency) -> bool:
        if frequency == "daily":
            return True
        if frequency == "weekly":
            return today.weekday() == 0  # lunedì
        if frequency == "monthly":
            return today.day == 1
        return False  # ad_hoc: solo manuale

    created_count = 0
    templates = (
        ChecklistTemplate.objects.filter(is_active=True)
        .select_related("plant")
        .prefetch_related("items")
    )
    for template in templates:
        if not _is_due_today(template.frequency):
            continue
        if template.plant_id:
            target_plants = [template.plant]
        else:
            # plant null → template valido per tutti i plant attivi
            target_plants = list(Plant.objects.filter(status="attivo"))
        for plant in target_plants:
            already = ChecklistRun.objects.filter(
                template=template, plant=plant, due_date=today
            ).exists()
            services.create_run_for_template(template, plant, today)
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

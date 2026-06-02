"""Management command: registra il job OSINT settimanale nel Celery beat schedule."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Registra o aggiorna il job OSINT weekly scanner nel Celery beat."

    def handle(self, *args, **options):
        from django_celery_beat.models import CrontabSchedule, PeriodicTask

        # Ogni lunedì alle 02:00 (Europe/Rome). Il nome coincide con la chiave del
        # beat_schedule in core/celery.py ("osint-weekly-scan"): così, se mai una
        # sincronizzazione del DatabaseScheduler girasse, farebbe update_or_create
        # sulla stessa riga invece di crearne una seconda (doppio scan settimanale,
        # come accaduto per il backup "Backup automatico notturno"/"auto-backup-daily").
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute="0",
            hour="2",
            day_of_week="1",  # lunedì
            day_of_month="*",
            month_of_year="*",
            timezone="Europe/Rome",
        )
        task, created = PeriodicTask.objects.update_or_create(
            name="osint-weekly-scan",
            defaults={
                "task": "osint.weekly_scan",
                "crontab": schedule,
                "enabled": True,
                "description": "Scan OSINT settimanale di tutte le entità attive (lunedì 02:00 Europe/Rome)",
            },
        )
        status = "creato" if created else "aggiornato"
        self.stdout.write(self.style.SUCCESS(f"Job OSINT weekly scanner {status}: {task.name}"))

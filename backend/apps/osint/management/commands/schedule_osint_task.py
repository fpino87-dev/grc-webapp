"""Management command: registra il job OSINT settimanale nel Celery beat schedule."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Registra o aggiorna il job OSINT weekly scanner nel Celery beat."

    def handle(self, *args, **options):
        from django_celery_beat.models import CrontabSchedule, PeriodicTask

        # Ogni lunedì alle 04:00 (Europe/Rome) — fuori dalla finestra del backup
        # notturno (02:00). Il nome coincide con la chiave in
        # settings.CELERY_BEAT_SCHEDULE ("osint-weekly-scan"), così beat e command
        # fanno update_or_create sulla stessa riga (niente doppione). Tenere i due
        # orari allineati se si modifica la pianificazione.
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute="0",
            hour="4",
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
                "description": "Scan OSINT settimanale di tutte le entità attive (lunedì 04:00 Europe/Rome)",
            },
        )
        status = "creato" if created else "aggiornato"
        self.stdout.write(self.style.SUCCESS(f"Job OSINT weekly scanner {status}: {task.name}"))

"""Management command: registra il job OSINT settimanale nel Celery beat schedule."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Registra o aggiorna il job OSINT weekly scanner nel Celery beat."

    def handle(self, *args, **options):
        from django_celery_beat.models import CrontabSchedule, PeriodicTask

        # Ogni lunedì alle 02:00
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute="0",
            hour="2",
            day_of_week="1",  # lunedì
            day_of_month="*",
            month_of_year="*",
        )
        task, created = PeriodicTask.objects.update_or_create(
            name="OSINT Weekly Scanner",
            defaults={
                "task": "osint.weekly_scan",
                "crontab": schedule,
                "enabled": True,
                "description": "Scan OSINT settimanale di tutte le entità attive (lunedì 02:00)",
            },
        )
        status = "creato" if created else "aggiornato"
        self.stdout.write(self.style.SUCCESS(f"Job OSINT weekly scanner {status}: {task.name}"))

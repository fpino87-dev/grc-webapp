from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Registra/aggiorna il PeriodicTask Celery Beat per il backup automatico notturno (02:00)."

    def handle(self, *args, **options):
        from django_celery_beat.models import CrontabSchedule, PeriodicTask

        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute="0",
            hour="2",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
        )

        task, created = PeriodicTask.objects.update_or_create(
            name="Backup automatico notturno",
            defaults={
                "task": "apps.backups.tasks.auto_backup_task",
                "crontab": schedule,
                "enabled": True,
            },
        )

        verb = "creato" if created else "aggiornato"
        self.stdout.write(self.style.SUCCESS(
            f"PeriodicTask '{task.name}' {verb} — crontab: 0 2 * * * (ogni notte alle 02:00)"
        ))

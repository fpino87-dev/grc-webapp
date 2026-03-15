import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.dev")
app = Celery("grc")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "check-expired-evidences": {
        "task": "apps.controls.tasks.check_expired_evidences",
        "schedule": crontab(hour=2, minute=0),
    },
    "generate-weekly-kpi-snapshots": {
        "task": "apps.reporting.tasks.generate_weekly_kpi_snapshots",
        "schedule": crontab(hour=6, minute=0, day_of_week=1),  # Monday 06:00
    },
    "check-unrevalued-changes": {
        "task": "apps.assets.tasks.check_unrevalued_changes",
        "schedule": crontab(hour=7, minute=0, day_of_week=1),  # Monday 07:00
    },
}


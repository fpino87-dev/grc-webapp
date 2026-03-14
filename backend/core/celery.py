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
}


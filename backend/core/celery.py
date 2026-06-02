import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.dev")
app = Celery("grc")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# NB: la pianificazione periodica vive in settings.CELERY_BEAT_SCHEDULE.
# In precedenza era ridichiarata qui come `app.conf.beat_schedule = {...}`, ma
# quell'assegnazione veniva SOVRASCRITTA dall'applicazione lazy di
# `config_from_object("django.conf:settings")`: era di fatto codice morto e le
# nuove voci aggiunte qui non venivano mai schedulate dal DatabaseScheduler.
# Unica fonte di verità: settings.CELERY_BEAT_SCHEDULE.


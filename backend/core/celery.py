# govrico - Governance, Risk & Compliance Platform
# Copyright (C) 2025 govrico
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

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


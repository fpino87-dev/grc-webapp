"""Verifica che la pianificazione attesa (settings.CELERY_BEAT_SCHEDULE) sia
effettivamente registrata come PeriodicTask nel DatabaseScheduler.

Nasce da un incidente reale: voci aggiunte a `beat_schedule` non finivano nelle
PeriodicTask (il DatabaseScheduler esegue dal DB) → job di compliance che non
partivano mai, in silenzio. Questo comando rende il drift **visibile** ed è
usabile in CI/health: esce con codice ≠ 0 se manca/è disabilitata/ha orario
diverso una qualsiasi voce attesa.

Uso:
    python manage.py verify_schedule              # fallisce (exit 1) se ci sono problemi
    python manage.py verify_schedule --report-only # stampa soltanto, exit 0
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

# Task gestiti fuori da settings (via management command dedicato) → leciti come
# "extra" nel DB, non vanno segnalati come problema.
_KNOWN_EXTERNAL = {
    "Backup automatico notturno",   # apps.backups schedule_backup_task
    "celery.backend_cleanup",       # interno celery
}


def _expected_fields(schedule):
    """(minute, hour, day_of_week, day_of_month, month_of_year) da un crontab celery,
    o None se la schedule non è un crontab (interval/solar)."""
    if not all(hasattr(schedule, f"_orig_{p}") for p in
               ("minute", "hour", "day_of_week", "day_of_month", "month_of_year")):
        return None
    return tuple(
        str(getattr(schedule, f"_orig_{p}"))
        for p in ("minute", "hour", "day_of_week", "day_of_month", "month_of_year")
    )


def _actual_fields(crontab):
    return (crontab.minute, crontab.hour, crontab.day_of_week,
            crontab.day_of_month, crontab.month_of_year)


def classify(schedule, periodic_task):
    """Ritorna (status, detail). status ∈ {OK, MISSING, DISABLED, MISMATCH}."""
    if periodic_task is None:
        return "MISSING", "nessuna PeriodicTask con questo nome"
    if not periodic_task.enabled:
        return "DISABLED", "PeriodicTask presente ma disabilitata"
    expected = _expected_fields(schedule)
    if expected is None:
        return "OK", "schedule non-crontab (confronto orario saltato)"
    if periodic_task.crontab is None:
        return "MISMATCH", "atteso crontab, la PeriodicTask non usa un crontab"
    actual = _actual_fields(periodic_task.crontab)
    if expected != actual:
        return "MISMATCH", f"atteso {expected}, trovato {actual}"
    return "OK", ""


def evaluate_all():
    """Confronta settings.CELERY_BEAT_SCHEDULE con le PeriodicTask a DB.
    Ritorna lista di (name, status, detail). Riusato da comando e health check."""
    from django_celery_beat.models import PeriodicTask

    beat = getattr(settings, "CELERY_BEAT_SCHEDULE", {}) or {}
    pts = {pt.name: pt for pt in PeriodicTask.objects.all()}
    return [
        (name, *classify(beat[name].get("schedule"), pts.get(name)))
        for name in sorted(beat)
    ]


class Command(BaseCommand):
    help = "Verifica che settings.CELERY_BEAT_SCHEDULE sia allineato alle PeriodicTask a DB."

    def add_arguments(self, parser):
        parser.add_argument(
            "--report-only", action="store_true",
            help="Stampa il report senza far fallire il comando (exit 0).",
        )

    def handle(self, *args, **options):
        from django_celery_beat.models import PeriodicTask

        beat = getattr(settings, "CELERY_BEAT_SCHEDULE", {}) or {}
        pts = {pt.name: pt for pt in PeriodicTask.objects.all()}

        problems = []
        self.stdout.write(f"Verifica pianificazione — {len(beat)} voci attese in settings\n")
        for name, status, detail in evaluate_all():
            mark = "✓" if status == "OK" else "✗"
            line = f"  {mark} {status:9s} {name}"
            if detail and status != "OK":
                line += f" — {detail}"
            self.stdout.write(line)
            if status != "OK":
                problems.append((name, status, detail))

        # Extra a DB non previsti in settings (solo informativo, esclusi i gestiti).
        extras = [n for n in pts if n not in beat and n not in _KNOWN_EXTERNAL]
        for n in sorted(extras):
            self.stdout.write(f"  · EXTRA     {n} (a DB, non in settings — verificare se atteso)")

        if problems:
            msg = f"{len(problems)} voce/i pianificate non allineate a DB (manca/disabilitata/orario diverso)."
            if options["report_only"]:
                self.stdout.write(self.style.WARNING(msg))
            else:
                raise CommandError(msg)
        else:
            self.stdout.write(self.style.SUCCESS("Pianificazione allineata: tutte le voci attese sono a DB e attive."))

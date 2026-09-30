"""Management command: diagnosi delle scansioni OSINT.

Risponde a «perché vedo dati vecchi?»: dice se lo scan settimanale è
pianificato e quando è girato, quante entità hanno l'ultimo scan riuscito
recente, e per quelle ferme qual è stato l'esito degli ultimi tentativi.
Sola lettura, salvo `--rescan` che rimette in coda le entità ferme.
"""
from collections import Counter

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Diagnosi scansioni OSINT: pianificazione, età dei dati, motivi dei fallimenti."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days", type=int, default=35,
            help="Un'entità è «ferma» se l'ultimo scan riuscito è più vecchio di N giorni (default 35).",
        )
        parser.add_argument(
            "--rescan", action="store_true",
            help="Mette in coda una nuova scansione per ogni entità ferma (come «Forza rescan»).",
        )

    def handle(self, *args, **options):
        from django_celery_beat.models import PeriodicTask

        from apps.osint.models import OsintEntity, OsintScan
        from apps.osint.validators import target_reachability

        now = timezone.now()
        days = options["days"]

        self.stdout.write(self.style.MIGRATE_HEADING("Pianificazione"))
        tasks = PeriodicTask.objects.filter(task__startswith="osint.").order_by("name")
        if not tasks:
            self.stdout.write(self.style.ERROR(
                "  nessun job OSINT registrato in celery-beat: gli scan automatici non partono "
                "(riavviare celery-beat o lanciare schedule_osint_task)"
            ))
        for t in tasks:
            line = f"  {t.name}: {'attivo' if t.enabled else 'DISATTIVATO'}, ultima esecuzione {t.last_run_at or 'mai'}"
            self.stdout.write(line if t.enabled and t.last_run_at else self.style.WARNING(line))

        entities = list(OsintEntity.objects.filter(is_active=True, deleted_at__isnull=True))
        stale = [e for e in entities if e.last_scan_at is None or (now - e.last_scan_at).days > days]
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Entità attive: {len(entities)} — ferme da più di {days} giorni: {len(stale)}"
        ))

        running = OsintScan.objects.filter(status="running", scan_date__lt=now - timezone.timedelta(hours=2)).count()
        if running:
            self.stdout.write(self.style.WARNING(
                f"  {running} scan rimasti «in corso» da oltre 2 ore (task interrotti)"
            ))

        reasons = Counter()
        for e in sorted(stale, key=lambda x: (x.entity_type, x.domain)):
            last = OsintScan.objects.filter(entity=e).order_by("-scan_date").first()
            if last is None:
                category = reason = "mai scansionata (lo scan settimanale non l'ha mai raggiunta)"
            elif last.status == "completed":
                category = reason = "nessun tentativo dopo l'ultimo scan riuscito (scan non pianificato o non eseguito)"
            else:
                errors = last.enricher_errors or {}
                if set(errors.values()) == {"non_public_target"}:
                    category = f"dominio non raggiungibile dal server (risoluzione: {target_reachability(e.domain)})"
                    detail = category
                else:
                    category = f"tentativi {last.status} per errori degli enricher"
                    detail = "; ".join(f"{k}: {v}" for k, v in list(errors.items())[:4]) or "nessun dettaglio"
                reason = f"ultimo tentativo {last.status} il {last.scan_date:%Y-%m-%d} — {detail}"
            reasons[category] += 1
            ok = e.last_scan_at.strftime("%Y-%m-%d") if e.last_scan_at else "mai"
            self.stdout.write(f"  [{e.entity_type}/{e.scan_frequency}] {e.domain} — ultimo riuscito: {ok} — {reason}")

        if reasons:
            self.stdout.write(self.style.MIGRATE_HEADING("Riepilogo cause"))
            for reason, n in reasons.most_common():
                self.stdout.write(f"  {n} × {reason}")

        if options["rescan"] and stale:
            from apps.osint.tasks import run_entity_scan

            for e in stale:
                run_entity_scan.delay(str(e.pk))
            self.stdout.write(self.style.SUCCESS(
                f"Scansione messa in coda per {len(stale)} entità: rilanciare il comando fra qualche minuto."
            ))

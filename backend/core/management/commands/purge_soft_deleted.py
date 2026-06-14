"""Purge definitivo dei record soft-deleted oltre la retention (GDPR Art. 5.1.e/17).

I record `soft_delete()`-ati restano nel DB (recuperabili). Oltre il periodo di
retention vanno eliminati definitivamente. Operazione **irreversibile** → di default
è in dry-run; serve `--apply` per cancellare davvero.

NB: l'AuditLog è immutabile e NON viene toccato (non è soft-deletable).
"""
from __future__ import annotations

from django.apps import apps as django_apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import ProtectedError
from django.utils import timezone


def _soft_delete_models():
    """Modelli con campo `deleted_at` e manager che espone `all_with_deleted`."""
    for model in django_apps.get_models():
        try:
            model._meta.get_field("deleted_at")
        except Exception:
            continue
        if hasattr(model.objects, "all_with_deleted"):
            yield model


class Command(BaseCommand):
    help = "Elimina definitivamente i record soft-deleted oltre la retention (dry-run salvo --apply)."

    def add_arguments(self, parser):
        default_days = getattr(settings, "SOFT_DELETE_PURGE_DAYS", 365)
        parser.add_argument("--days", type=int, default=default_days,
                            help=f"Età minima (giorni) del soft-delete da purgare. Default {default_days}.")
        parser.add_argument("--apply", action="store_true",
                            help="Esegue la cancellazione (senza, è solo un'anteprima).")

    def handle(self, *args, **options):
        cutoff = timezone.now() - timezone.timedelta(days=options["days"])
        apply = options["apply"]
        mode = "APPLY" if apply else "DRY-RUN"
        self.stdout.write(f"[{mode}] purge soft-deleted con deleted_at < {cutoff.date()}")

        total = 0
        for model in _soft_delete_models():
            qs = model.objects.all_with_deleted().filter(deleted_at__lt=cutoff)
            n = qs.count()
            if not n:
                continue
            label = f"{model._meta.app_label}.{model._meta.object_name}"
            if apply:
                try:
                    deleted, _ = qs.delete()
                    self.stdout.write(f"  {label}: eliminati {deleted}")
                    total += deleted
                except ProtectedError:
                    self.stderr.write(self.style.WARNING(
                        f"  {label}: {n} bloccati da FK PROTECT — saltati"
                    ))
            else:
                self.stdout.write(f"  {label}: {n} candidati")
                total += n

        verb = "eliminati" if apply else "candidati (dry-run)"
        self.stdout.write(self.style.SUCCESS(f"Totale {verb}: {total}"))
        if not apply and total:
            self.stdout.write("Rilancia con --apply per eliminare definitivamente.")

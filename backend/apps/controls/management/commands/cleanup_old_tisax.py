"""
Management command: python manage.py cleanup_old_tisax

Rimuove (soft-delete) i Control e ControlInstance TISAX che hanno ancora
i vecchi external_id in formato "TISAX-L2-*" / "TISAX-L3-*" (pre VDA ISA 6.0).

Il comando load_frameworks usa update_or_create su (framework, external_id):
i nuovi controlli ISA-X.Y.Z vengono creati correttamente, ma i vecchi con
external_id differente rimangono orfani. Questo comando li elimina prima
di eseguire load_frameworks con i nuovi JSON.

Sequenza corretta:
    python manage.py cleanup_old_tisax
    python manage.py load_frameworks
"""
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Soft-delete controlli TISAX con vecchi external_id (TISAX-L2-*, TISAX-L3-*)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Mostra cosa verrebbe eliminato senza modificare il DB",
        )

    def handle(self, *args, **options):
        from apps.controls.models import Control, ControlInstance, Framework

        dry = options["dry_run"]

        frameworks = Framework.objects.filter(code__in=["TISAX_L2", "TISAX_L3"])
        if not frameworks.exists():
            self.stdout.write("Nessun framework TISAX_L2/TISAX_L3 nel DB — niente da fare.")
            return

        total_ctrl = 0
        total_inst = 0

        with transaction.atomic():
            for fw in frameworks:
                # I vecchi external_id iniziavano con "TISAX-" (es. "TISAX-L2-IS-1.1")
                old_controls = Control.objects.filter(
                    framework=fw,
                    external_id__startswith="TISAX-",
                    deleted_at__isnull=True,
                )
                n_ctrl = old_controls.count()
                if n_ctrl == 0:
                    self.stdout.write(f"  {fw.code}: nessun controllo con vecchio external_id.")
                    continue

                old_instances = ControlInstance.objects.filter(
                    control__in=old_controls,
                    deleted_at__isnull=True,
                )
                n_inst = old_instances.count()

                self.stdout.write(
                    f"  {fw.code}: {n_ctrl} controlli obsoleti, {n_inst} istanze attive"
                )

                if not dry:
                    for inst in old_instances:
                        inst.soft_delete()
                    for ctrl in old_controls:
                        ctrl.soft_delete()

                total_ctrl += n_ctrl
                total_inst += n_inst

        if dry:
            self.stdout.write(self.style.WARNING(
                f"[DRY-RUN] Verrebbero soft-deleted: "
                f"{total_ctrl} controlli, {total_inst} istanze."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"cleanup_old_tisax completato: "
                f"{total_ctrl} controlli, {total_inst} istanze soft-deleted."
            ))

from django.core.management.base import BaseCommand

from apps.suppliers.models import SupplierEvaluationConfig


class Command(BaseCommand):
    help = (
        "Inizializza la configurazione singleton SupplierEvaluationConfig "
        "con pesi, label parametri e soglie di default."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Sovrascrive la configurazione esistente con i default.",
        )

    def handle(self, *args, **options):
        existing = SupplierEvaluationConfig.objects.first()
        if existing and not options["reset"]:
            self.stdout.write(self.style.WARNING(
                "Configurazione già presente — usa --reset per sovrascrivere."
            ))
            return

        if existing:
            existing.weights = SupplierEvaluationConfig.DEFAULT_WEIGHTS.copy()
            existing.parameter_labels = {
                k: v.copy() for k, v in SupplierEvaluationConfig.DEFAULT_PARAMETER_LABELS.items()
            }
            existing.risk_thresholds = SupplierEvaluationConfig.DEFAULT_RISK_THRESHOLDS.copy()
            existing.assessment_validity_months = 12
            existing.nis2_concentration_bump = True
            existing.save()
            self.stdout.write(self.style.SUCCESS("Configurazione resettata ai default."))
            return

        SupplierEvaluationConfig.get_solo()
        self.stdout.write(self.style.SUCCESS("Configurazione creata con i default."))

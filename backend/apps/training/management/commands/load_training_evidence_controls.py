from django.core.management.base import BaseCommand

from apps.controls.models import Control
from apps.training.models import TrainingEvidenceControl

# Controlli che un'erogazione prova, per tipo di destinatari: sono i valori
# iniziali, poi si modificano dall'interfaccia (Formazione → Catalogo corsi).
# Si aggiungono solo i controlli dei framework caricati e non archiviati; nulla
# viene tolto. L'organo di gestione non ha un controllo dedicato nei framework:
# la sua formazione la misura il KPI board_training_valid.
DEFAULTS = {
    "generale": ["ACN-NIS2-PR.AT-01", "A.6.3", "NIS2-ART21-7.1", "ISA-2.1.3"],
    "ruoli_critici": ["ACN-NIS2-PR.AT-02", "A.6.3"],
    "organo_gestione": [],
}


class Command(BaseCommand):
    help = "Carica i controlli predefiniti provati dalle erogazioni della formazione"

    def handle(self, *args, **options):
        created = 0
        for audience_kind, codes in DEFAULTS.items():
            controls = Control.objects.filter(
                external_id__in=codes, framework__archived_at__isnull=True,
            )
            for control in controls:
                _, was_created = TrainingEvidenceControl.objects.get_or_create(
                    audience_kind=audience_kind, control=control,
                )
                created += was_created
        self.stdout.write(self.style.SUCCESS(f"Controlli della formazione aggiunti: {created}"))

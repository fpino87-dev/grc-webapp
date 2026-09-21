"""Anteprima della migrazione training.0004 (formazione a evidenze).

Da lanciare in produzione PRIMA di `migrate`. Non modifica nulla: mostra quali
riferimenti normativi dei corsi diventano collegamenti ai controlli (e quali non
trovano un controllo) e quante sessioni storiche nasceranno dai dati per persona.

    python manage.py check_training_migration_readiness

Exit code sempre 0: i riferimenti non trovati non bloccano la migrazione, vanno
solo ricollegati a mano dalla scheda del corso.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Anteprima in sola lettura della migrazione dei dati di formazione (training.0004)."

    def handle(self, *args, **options):
        from apps.controls.models import Control
        from apps.plants.models import Plant
        from apps.training.legacy import plan_legacy_migration
        from apps.training.models import PhishingSimulation, TrainingCourse, TrainingEnrollment

        plan = plan_legacy_migration(
            TrainingCourse, TrainingEnrollment, PhishingSimulation, Control, Plant,
        )
        plant_codes = dict(Plant.objects.values_list("pk", "code"))

        def site(pid):
            return plant_codes.get(pid, "—") if pid else "tutti i siti"

        links = sum(len(r["control_ids"]) for r in plan["course_controls"])
        self.stdout.write(
            f"Corsi con riferimenti collegati ai controlli: {len(plan['course_controls'])}"
            f" ({links} collegamenti)"
        )
        if plan["unmatched_refs"]:
            self.stdout.write(self.style.WARNING(
                "\nRiferimenti senza controllo corrispondente (da ricollegare a mano):"
            ))
            for r in plan["unmatched_refs"]:
                self.stdout.write(f"   {r['course']}: {r['ref']}")

        self.stdout.write(
            f"\nSessioni storiche dalle iscrizioni: {len(plan['enrollment_sessions'])}"
        )
        for r in plan["enrollment_sessions"]:
            self.stdout.write(
                f"   {r['course']} [{site(r['plant_id'])}] {r['held_on']}:"
                f" {r['trained_count']}/{r['target_count']} completate"
            )
        self.stdout.write(
            f"\nSessioni storiche di phishing: {len(plan['phishing_sessions'])}"
        )
        for r in plan["phishing_sessions"]:
            self.stdout.write(
                f"   {r['held_on']} [{site(r['plant_id'])}]: inviate {r['sent_count']},"
                f" clic {r['clicked_count']}, segnalate {r['reported_count']}"
            )
        self.stdout.write(self.style.SUCCESS(
            "\nNessuna modifica eseguita. I dati per persona restano intatti dopo la migrazione."
        ))

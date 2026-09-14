"""
Management command: python manage.py dedupe_role_assignments

Trova le assegnazioni di ruolo duplicate — stesso utente, stesso ruolo, stesso
perimetro, tutte senza data di fine — e (opzionalmente) le rimuove con soft
delete, tenendo la nomina più vecchia. Ogni rimozione è registrata nell'audit
trail (`governance.role_assignment.duplicate_removed`).

Segnala anche i ruoli a titolare unico con più titolari *diversi* attivi sullo
stesso perimetro: questi NON vengono toccati, perché chi resta lo decide il
responsabile da Governance → Sostituisci / Termina.

La migrazione governance 0008 esegue la stessa pulizia durante `migrate`
(audit attribuito al primo superuser attivo). Il comando serve per vedere in
anteprima cosa verrà rimosso, o per eseguire la pulizia firmandola con un
utente preciso.

Uso:
    # Anteprima (default): nessuna modifica
    python manage.py dedupe_role_assignments

    # Applica la pulizia
    python manage.py dedupe_role_assignments --apply --user admin@azienda.it

Nell'output gli utenti compaiono solo per id (niente email: regola #11).
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Trova (e con --apply rimuove) le assegnazioni di ruolo duplicate; segnala i conflitti di titolare unico."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Esegue il soft delete dei doppioni.")
        parser.add_argument("--user", help="Email dell'utente che firma l'audit (obbligatorio con --apply).")

    def handle(self, *args, **options):
        from apps.governance.services import (
            cleanup_duplicate_role_assignments,
            find_duplicate_role_assignments,
            find_single_holder_conflicts,
        )

        duplicates = find_duplicate_role_assignments()
        conflicts = find_single_holder_conflicts()
        scope_label = self._scope_labeler(duplicates + conflicts)

        if duplicates:
            self.stdout.write(f"Nomine duplicate (stesso utente, ruolo e perimetro): {len(duplicates)} gruppi")
            for g in duplicates:
                self.stdout.write(
                    f"  {g['role']} @ {scope_label(g['scope_type'], g['scope_id'])} — utente id {g['user_id']}: "
                    f"tengo {g['keep'].pk} (dal {g['keep'].valid_from}), "
                    f"rimuovo {', '.join(str(d.pk) for d in g['remove'])}"
                )
        else:
            self.stdout.write(self.style.SUCCESS("Nessuna nomina duplicata."))

        if conflicts:
            self.stdout.write(self.style.WARNING(
                f"\nRuoli a titolare unico con più titolari diversi (da risolvere a mano "
                f"in Governance con Sostituisci o Termina): {len(conflicts)}"
            ))
            for c in conflicts:
                self.stdout.write(
                    f"  {c['role']} @ {scope_label(c['scope_type'], c['scope_id'])} — "
                    f"utenti id {', '.join(str(u) for u in c['user_ids'])}"
                )

        if not duplicates:
            return
        if not options["apply"]:
            self.stdout.write(self.style.WARNING("\nDRY-RUN — nessuna modifica. Per applicare: --apply --user <email>"))
            return
        if not options["user"]:
            raise CommandError("--apply richiede --user <email> per firmare l'audit trail.")
        actor = get_user_model().objects.filter(email=options["user"], is_active=True).first()
        if actor is None:
            raise CommandError("Utente indicato con --user non trovato o non attivo.")

        removed = cleanup_duplicate_role_assignments(actor)
        self.stdout.write(self.style.SUCCESS(
            f"\nRimosse {removed} nomine duplicate. Audit: governance.role_assignment.duplicate_removed"
        ))

    @staticmethod
    def _scope_labeler(groups):
        from apps.plants.models import BusinessUnit, Plant

        plant_ids = {g["scope_id"] for g in groups if g["scope_type"] == "plant" and g["scope_id"]}
        bu_ids = {g["scope_id"] for g in groups if g["scope_type"] == "bu" and g["scope_id"]}
        plants = dict(Plant.objects.filter(id__in=plant_ids).values_list("id", "code"))
        bus = dict(BusinessUnit.objects.filter(id__in=bu_ids).values_list("id", "code"))

        def label(scope_type, scope_id):
            if scope_type == "org":
                return "org"
            codes = plants if scope_type == "plant" else bus
            return f"{scope_type} {codes.get(scope_id, scope_id)}"

        return label

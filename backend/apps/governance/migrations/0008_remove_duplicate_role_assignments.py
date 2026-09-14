"""Rimuove le assegnazioni di ruolo duplicate prima del vincolo di unicità (0009).

Prima del fix del 2026-06-23 era possibile nominare più volte lo stesso utente
sullo stesso ruolo e perimetro (es. tre "Contatto NIS2" identici sullo stesso
sito). Il vincolo `uniq_open_role_assignment` non si può creare finché quelle
righe esistono: qui si tiene la nomina più vecchia e si rimuovono le altre con
soft delete, registrando ciascuna rimozione nell'audit trail.

Anteprima senza modifiche: `python manage.py dedupe_role_assignments`.
"""
from django.db import migrations


def remove_duplicate_open_assignments(apps, schema_editor):
    # Servizi e modelli "vivi" invece dello stato storico: la rimozione deve
    # passare dall'audit trail (regola #3), che è fuori da questa app. Su un DB
    # senza doppioni (installazioni nuove, CI) la funzione esce subito.
    from apps.governance.services import (
        cleanup_duplicate_role_assignments,
        find_duplicate_role_assignments,
        system_actor,
    )

    if not find_duplicate_role_assignments():
        return
    actor = system_actor()
    if actor is None:
        raise RuntimeError(
            "Ci sono assegnazioni di ruolo duplicate da rimuovere ma nessun "
            "superuser attivo a cui attribuire l'audit. Esegui prima: "
            "python manage.py dedupe_role_assignments --apply --user <email>"
        )
    cleanup_duplicate_role_assignments(actor)


class Migration(migrations.Migration):

    dependencies = [
        ("governance", "0007_rolerequirement_mandatory_and_more"),
    ]

    operations = [
        migrations.RunPython(remove_duplicate_open_assignments, migrations.RunPython.noop),
    ]

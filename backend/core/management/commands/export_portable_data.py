"""Export portabile dei dati (GDPR Art. 20 / Data Act): dump JSON machine-readable.

Esporta i dati di dominio govrico in JSON standard (Django serialization), formato
aperto e re-importabile, per evitare lock-in e abilitare la portabilità verso un
altro sistema. Esclude le tabelle infrastrutturali (sessioni, admin, contenttypes,
token blacklist, risultati Celery) e l'audit log immutabile.
"""
from __future__ import annotations

import datetime
from io import StringIO
from pathlib import Path

from django.apps import apps as django_apps
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Esporta i dati di dominio govrico in un file JSON portabile (Data Act / Art. 20)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output", type=str, default="",
            help="Percorso file di output (.json). Default: BACKUP_DIR/govrico_export_<ts>.json",
        )
        parser.add_argument("--indent", type=int, default=2, help="Indentazione JSON.")

    def handle(self, *args, **options):
        # App di dominio = quelle sotto 'apps.*' + gli utenti (auth.User).
        app_labels = sorted(
            cfg.label for cfg in django_apps.get_app_configs()
            if cfg.name.startswith("apps.")
        )
        targets = ["auth.User", *app_labels]

        out_path = options["output"]
        if not out_path:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            base = getattr(settings, "BACKUP_DIR", ".")
            out_path = str(Path(base) / f"govrico_export_{ts}.json")

        Path(out_path).parent.mkdir(parents=True, exist_ok=True)

        buf = StringIO()
        # `dumpdata` con natural keys → più portabile (no PK numeriche dipendenti dal DB).
        call_command(
            "dumpdata", *targets,
            format="json", indent=options["indent"],
            natural_foreign=True, natural_primary=True,
            stdout=buf,
        )
        data = buf.getvalue()
        Path(out_path).write_text(data, encoding="utf-8")

        size_kb = round(len(data.encode("utf-8")) / 1024, 1)
        self.stdout.write(self.style.SUCCESS(
            f"Export portabile creato: {out_path} ({size_kb} KB) — {len(targets)} gruppi di modelli."
        ))
        self.stdout.write(
            "Nota: contiene dati personali → conservare in luogo sicuro; "
            "l'audit log immutabile è escluso per progetto."
        )

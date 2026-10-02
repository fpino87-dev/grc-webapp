"""Carica il catalogo minacce di gruppo da backend/risk_catalogs/threats.json.

Idempotente: aggiorna le voci del catalogo per codice, disattiva quelle tolte
dal file e non tocca le voci personalizzate create da UI. Crea anche gli
obiettivi aziendali proposti (risk_catalogs/business_objectives.json) che
mancano, senza toccare quelli modificati o eliminati.
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Importa il catalogo minacce (risk_catalogs/threats.json)"

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        from apps.risk.services import sync_threat_catalog

        path = Path(options["file"]) if options["file"] else (
            Path(__file__).resolve().parents[4] / "risk_catalogs" / "threats.json"
        )
        if not path.exists():
            raise CommandError(f"File non trovato: {path}")
        data = json.loads(path.read_text("utf-8"))
        threats = data.get("threats", [])
        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(f"[DRY-RUN] {len(threats)} minacce in {path.name}"))
            return
        counts = sync_threat_catalog(data)
        self.stdout.write(self.style.SUCCESS(
            f"Catalogo {data.get('version', '')}: {counts['created']} create, "
            f"{counts['updated']} aggiornate, {counts['deactivated']} disattivate"
        ))
        objectives_path = path.parent / "business_objectives.json"
        if not options["file"] and objectives_path.exists():
            from apps.risk.services import seed_business_objectives

            created = seed_business_objectives(json.loads(objectives_path.read_text("utf-8")).get("objectives", []))
            self.stdout.write(self.style.SUCCESS(f"Obiettivi aziendali proposti: {created} creati"))
        if counts["conflicts"]:
            self.stdout.write(self.style.WARNING(
                "Codici già usati da voci personalizzate (non importati): "
                + ", ".join(counts["conflicts"])
            ))

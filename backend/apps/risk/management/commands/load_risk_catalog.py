"""Carica il catalogo minacce di gruppo da backend/risk_catalogs/threats.json.

Idempotente: aggiorna le voci del catalogo per codice, disattiva quelle tolte
dal file e non tocca le voci personalizzate create da UI.
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
        if counts["conflicts"]:
            self.stdout.write(self.style.WARNING(
                "Codici già usati da voci personalizzate (non importati): "
                + ", ".join(counts["conflicts"])
            ))

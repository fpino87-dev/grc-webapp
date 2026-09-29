"""Genera la copia PDF delle versioni Word dei documenti (M07).

Da lanciare una volta dopo l'aggiornamento che introduce la conversione, per i
documenti già caricati; poi ci pensano il caricamento e il passaggio notturno.

    python manage.py convert_document_pdfs              # versioni "da generare"
    python manage.py convert_document_pdfs --retry-failed
"""

from django.core.management.base import BaseCommand

from apps.documents import pdf_converter
from apps.documents.services import generate_pending_pdfs


class Command(BaseCommand):
    help = "Genera la copia PDF delle versioni Word dei documenti."

    def add_arguments(self, parser):
        parser.add_argument(
            "--retry-failed", action="store_true",
            help="Riprova anche le versioni la cui conversione era fallita.",
        )
        parser.add_argument("--limit", type=int, default=None, help="Numero massimo di versioni.")

    def handle(self, *args, **options):
        if not pdf_converter.is_enabled():
            self.stderr.write("GOTENBERG_URL non impostato: conversione disattivata.")
            return
        counts = generate_pending_pdfs(
            include_failed=options["retry_failed"], limit=options["limit"],
        )
        self.stdout.write(
            f"PDF generati: {counts.get('ok', 0)} — non convertibili: {counts.get('failed', 0)} "
            f"— senza file: {counts.get('na', 0)}"
        )
        if counts.get("pending"):
            self.stderr.write(
                "Servizio di conversione non raggiungibile: le versioni restanti "
                "restano in coda (controllare il container gotenberg)."
            )

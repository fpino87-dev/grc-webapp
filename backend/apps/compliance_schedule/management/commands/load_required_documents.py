"""
Management command: python manage.py load_required_documents

Populates RequiredDocument table with mandatory documents for
ISO 27001, NIS2, TISAX L2, TISAX L3.
Run after migrations.
"""
from django.core.management.base import BaseCommand
from apps.compliance_schedule.models import RequiredDocument

REQUIRED_DOCS = [
    # ── ISO 27001 ──────────────────────────────────────────────────────────────
    ("ISO27001", "policy",           "Politica per la sicurezza delle informazioni",       "A.5.1",   True),
    ("ISO27001", "procedure",        "Procedura gestione accessi logici",                  "A.8.3",   True),
    ("ISO27001", "procedure",        "Procedura gestione incidenti di sicurezza",          "A.6.8",   True),
    ("ISO27001", "procedure",        "Procedura backup e ripristino",                      "A.8.13",  True),
    ("ISO27001", "procedure",        "Procedura change management IT",                     "A.8.32",  True),
    ("ISO27001", "procedure",        "Procedura classificazione informazioni",              "A.5.12",  True),
    ("ISO27001", "procedure",        "Procedura gestione fornitori critici",               "A.5.19",  True),
    ("ISO27001", "record",           "Registro asset IT/OT",                               "A.5.9",   True),
    ("ISO27001", "record",           "Registro rischi aggiornato",                         "6.1.2",   True),
    ("ISO27001", "record",           "Dichiarazione di applicabilità (SOA)",               "6.1.3",   True),
    ("ISO27001", "record",           "Piano di trattamento del rischio (POA&M)",           "6.1.3",   True),
    ("ISO27001", "record",           "Verbali revisione della direzione",                  "9.3",     True),
    ("ISO27001", "record",           "Rapporti audit interno",                             "9.2",     True),
    ("ISO27001", "record",           "Log audit trail accessi privilegiati",               "A.8.15",  True),
    ("ISO27001", "record",           "Piano BCP/DR approvato",                             "A.5.30",  True),
    ("ISO27001", "record",           "Risultati test BCP",                                 "A.5.30",  False),
    ("ISO27001", "record",           "Registro formazione dipendenti",                     "A.6.3",   True),
    ("ISO27001", "procedure",        "Procedura crittografia e gestione chiavi",           "A.8.24",  True),
    ("ISO27001", "procedure",        "Procedura sicurezza fisica e ambientale",            "A.7.1",   True),
    ("ISO27001", "record",           "Analisi BIA",                                        "A.5.30",  False),

    # ── NIS2 ───────────────────────────────────────────────────────────────────
    ("NIS2",     "policy",           "Politica sicurezza reti e sistemi informativi",       "Art.21", True),
    ("NIS2",     "record",           "Valutazione rischi cyber aggiornata",                "Art.21", True),
    ("NIS2",     "procedure",        "Procedura notifica incidenti NIS2 (24h/72h)",        "Art.23", True),
    ("NIS2",     "record",           "Registro incidenti significativi",                   "Art.23", True),
    ("NIS2",     "procedure",        "Procedura business continuity e disaster recovery",  "Art.21", True),
    ("NIS2",     "record",           "Valutazione sicurezza supply chain",                 "Art.21", True),
    ("NIS2",     "procedure",        "Procedura crittografia e MFA",                       "Art.21", True),
    ("NIS2",     "record",           "Piano formazione sicurezza informatica",              "Art.21", True),
    ("NIS2",     "record",           "Evidenze test BCP annuali",                          "Art.21", False),
    ("NIS2",     "record",           "Contratti fornitori con clausole NIS2",              "Art.21", False),

    # ── TISAX L2 ───────────────────────────────────────────────────────────────
    ("TISAX_L2", "policy",           "Information Security Policy (ISP)",                  "1.1",    True),
    ("TISAX_L2", "record",           "Registro asset informativi classificati",             "2.1",    True),
    ("TISAX_L2", "procedure",        "Procedura accesso fisico aree protette",              "4.1",    True),
    ("TISAX_L2", "procedure",        "Procedura gestione identità e accessi (IAM)",         "3.1",    True),
    ("TISAX_L2", "record",           "Risultati assessment VDA ISA",                        "1.3",    True),
    ("TISAX_L2", "record",           "Piano trattamento rischi informativi",                "1.2",    True),
    ("TISAX_L2", "procedure",        "Procedura sicurezza sviluppo software",               "5.1",    False),
    ("TISAX_L2", "record",           "Registro eventi di sicurezza",                        "3.3",    True),
    ("TISAX_L2", "procedure",        "Procedura gestione vulnerabilità",                    "3.4",    True),
    ("TISAX_L2", "record",           "Accordi NDA con fornitori",                           "6.1",    True),

    # ── TISAX L3 ───────────────────────────────────────────────────────────────
    ("TISAX_L3", "policy",           "Information Security Policy (ISP) — Livello 3",      "1.1",    True),
    ("TISAX_L3", "record",           "Analisi rischi HSS/PPE approfondita",                "2.2",    True),
    ("TISAX_L3", "procedure",        "Procedura gestione prototipo fisico",                 "7.1",    True),
    ("TISAX_L3", "procedure",        "Procedura sicurezza veicoli e test drive",            "7.2",    True),
    ("TISAX_L3", "record",           "Registro accessi area prototipi",                     "4.2",    True),
    ("TISAX_L3", "procedure",        "Procedura distruzione sicura informazioni classificate", "2.3", True),
    ("TISAX_L3", "record",           "Risultati assessment TISAX L3 (terza parte)",         "1.3",   True),
    ("TISAX_L3", "record",           "Evidenze controlli crittografici rinforzati",         "3.2",   True),
    ("TISAX_L3", "procedure",        "Procedura risposta incidenti HSS",                    "6.2",   True),
    ("TISAX_L3", "record",           "Accordi NDA estesi con partner OEM",                  "6.1",   True),
]


class Command(BaseCommand):
    help = "Load mandatory document requirements for ISO27001, NIS2, TISAX_L2, TISAX_L3"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear existing records before loading")

    def handle(self, *args, **options):
        if options["clear"]:
            RequiredDocument.objects.all().delete()
            self.stdout.write("Cleared existing RequiredDocument records.")

        created = 0
        skipped = 0
        for framework, doc_type, description, iso_clause, mandatory in REQUIRED_DOCS:
            _, was_created = RequiredDocument.objects.get_or_create(
                framework=framework,
                document_type=doc_type,
                description=description,
                defaults={
                    "iso_clause": iso_clause,
                    "mandatory": mandatory,
                }
            )
            if was_created:
                created += 1
            else:
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"load_required_documents: {created} creati, {skipped} già presenti."
            )
        )

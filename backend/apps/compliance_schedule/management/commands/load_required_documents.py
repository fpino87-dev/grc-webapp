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
    # Catalogo documenti NIS2 generico rimosso 2026-08-06: NIS2 è una direttiva,
    # la documentazione dipende dalla trasposizione nazionale (in Italia
    # D.Lgs. 138/2024), dal settore e dalla classificazione dell'entità. Una lista
    # fissa sarebbe fuorviante. Il framework generico "NIS2" non è attivo su alcun
    # sito; la compliance concreta gira sui controlli "ACN_NIS2" (trasposizione
    # italiana). Nessun documento obbligatorio è definito qui per NIS2.

    # ── ACN_NIS2 (trasposizione italiana — controlli NIST CSF adattati ACN) ────
    # iso_clause = external_id COMPLETO del controllo ACN (necessario al resolver).
    # Le voci marcate [essential] mappano controlli con level="essential": la
    # logica di stato le mostra SOLO sui plant con nis2_scope="essenziale" (per gli
    # "importanti" il controllo non è istanziato → il documento è escluso).
    ("ACN_NIS2", "policy",    "Policy di gestione del rischio di cybersecurity",         "ACN-NIS2-GV.PO-01", True),
    ("ACN_NIS2", "record",    "Documento ruoli e responsabilità cybersecurity",          "ACN-NIS2-GV.RR-02", True),
    ("ACN_NIS2", "procedure", "Programma di gestione del rischio supply chain",           "ACN-NIS2-GV.SC-01", True),
    ("ACN_NIS2", "record",    "Registro fornitori con prioritizzazione",                 "ACN-NIS2-GV.SC-04", True),
    ("ACN_NIS2", "record",    "Clausole di sicurezza nei contratti con fornitori",       "ACN-NIS2-GV.SC-05", True),
    ("ACN_NIS2", "record",    "Inventario asset hardware",                               "ACN-NIS2-ID.AM-01", True),
    ("ACN_NIS2", "record",    "Inventario software, servizi e sistemi",                  "ACN-NIS2-ID.AM-02", True),
    ("ACN_NIS2", "record",    "Valutazione del rischio cyber (probabilità/impatto)",     "ACN-NIS2-ID.RA-05", True),
    ("ACN_NIS2", "record",    "Piano di trattamento del rischio",                        "ACN-NIS2-ID.RA-06", True),
    ("ACN_NIS2", "record",    "Registro delle vulnerabilità",                            "ACN-NIS2-ID.RA-01", True),
    ("ACN_NIS2", "procedure", "Piano di risposta agli incidenti",                        "ACN-NIS2-ID.IM-04", True),
    ("ACN_NIS2", "record",    "Mappa dei flussi di rete e dati",                         "ACN-NIS2-ID.AM-03", True),   # [essential]
    ("ACN_NIS2", "procedure", "Procedura gestione identità e accessi (IAM)",             "ACN-NIS2-PR.AA-01", True),
    ("ACN_NIS2", "procedure", "Procedura controllo accessi fisici",                      "ACN-NIS2-PR.AA-06", False),
    ("ACN_NIS2", "record",    "Piano di formazione e awareness cybersecurity",           "ACN-NIS2-PR.AT-01", True),
    ("ACN_NIS2", "procedure", "Procedura crittografia e protezione dati",                "ACN-NIS2-PR.DS-02", True),
    ("ACN_NIS2", "procedure", "Procedura backup e ripristino dati",                      "ACN-NIS2-PR.DS-11", True),
    ("ACN_NIS2", "procedure", "Procedura patch e aggiornamento software",                "ACN-NIS2-PR.PS-02", True),
    ("ACN_NIS2", "procedure", "Procedura gestione log e monitoraggio",                   "ACN-NIS2-PR.PS-04", True),
    ("ACN_NIS2", "procedure", "Procedura sviluppo software sicuro (SDLC)",               "ACN-NIS2-PR.PS-06", False),
    ("ACN_NIS2", "record",    "Piano formazione specialistica per ruoli critici",        "ACN-NIS2-PR.AT-02", True),   # [essential]
    ("ACN_NIS2", "record",    "Documentazione resilienza/ridondanza infrastruttura IT",  "ACN-NIS2-PR.IR-03", True),   # [essential]
    ("ACN_NIS2", "procedure", "Procedura gestione configurazioni sicure (hardening)",    "ACN-NIS2-PR.PS-01", True),   # [essential]
    ("ACN_NIS2", "procedure", "Procedura manutenzione hardware",                         "ACN-NIS2-PR.PS-03", False),  # [essential]
    ("ACN_NIS2", "procedure", "Procedura notifica incidenti significativi (ACN/CSIRT)",  "ACN-NIS2-RS.CO-02", True),
    ("ACN_NIS2", "record",    "Registro incidenti significativi",                        "ACN-NIS2-RS.MA-01", True),
    ("ACN_NIS2", "procedure", "Piano di continuità operativa e ripristino (BCP/DR)",     "ACN-NIS2-RC.RP-01", True),
    ("ACN_NIS2", "record",    "Piano di comunicazione durante il ripristino",            "ACN-NIS2-RC.CO-03", False),  # [essential]

    # ── TISAX L2 (VDA ISA 6.0 — numerazione ISA) ───────────────────────────────
    ("TISAX_L2", "policy",           "Information Security Policy (ISP)",                  "ISA 1.1.1",  True),
    ("TISAX_L2", "record",           "Registro asset informativi classificati",             "ISA 1.2.1",  True),
    ("TISAX_L2", "procedure",        "Procedura accesso fisico aree protette",              "ISA 4.1.1",  True),
    ("TISAX_L2", "procedure",        "Procedura gestione identità e accessi (IAM)",         "ISA 3.1.1",  True),
    ("TISAX_L2", "record",           "Risultati assessment VDA ISA",                        "ISA 1.3.4",  True),
    ("TISAX_L2", "record",           "Piano trattamento rischi informativi",                "ISA 1.2.2",  True),
    ("TISAX_L2", "procedure",        "Procedura sicurezza sviluppo software",               "ISA 5.1.1",  False),
    ("TISAX_L2", "record",           "Registro eventi di sicurezza",                        "ISA 5.2.3",  True),
    ("TISAX_L2", "procedure",        "Procedura gestione vulnerabilità",                    "ISA 5.2.2",  True),
    ("TISAX_L2", "record",           "Accordi NDA con fornitori",                           "ISA 6.1.1",  True),

    # ── TISAX L3 (VDA ISA 6.0 — requisiti Very High Protection) ────────────────
    # "Very High" aggiunge requisiti solo a un sottoinsieme di 12 controlli VH.
    # I documenti senza controllo VH dedicato (ISP, analisi rischi, distruzione
    # sicura, terze parti, NDA) sono coperti a livello L2 e NON sono elencati qui:
    # rimossi 2026-08-06 per allineamento al catalogo controlli reale. Le clausole
    # dei 5 documenti rimasti puntano a controlli VH esistenti.
    ("TISAX_L3", "procedure",        "Procedura autenticazione rinforzata (MFA)",           "ISA 4.1.2-VH", True),
    ("TISAX_L3", "record",           "Registro accessi aree Very High Protection",          "ISA 4.1.2-VH", True),
    ("TISAX_L3", "record",           "Risultati assessment TISAX AL3 (terza parte)",        "ISA 1.3.4-VH", True),
    ("TISAX_L3", "procedure",        "Procedura risposta incidenti Very High",              "ISA 1.6.2-VH", True),
    ("TISAX_L3", "record",           "Evidenze controlli crittografici rinforzati",         "ISA 5.1.2-VH", True),

    # ── TISAX Prototype Protection (VDA ISA 6.0 — Capitolo 8) ──────────────────
    ("TISAX_PROTO", "policy",        "Concetto di sicurezza prototipi (HSS/PPE)",           "ISA 8.1.1",  True),
    ("TISAX_PROTO", "record",        "Accordi NDA specifici per prototipi",                 "ISA 8.2.1",  True),
    ("TISAX_PROTO", "procedure",     "Procedura trasporto sicuro prototipi",                "ISA 8.3.1",  True),
    ("TISAX_PROTO", "record",        "Registro visitatori aree prototipo",                  "ISA 8.1.7",  True),
    ("TISAX_PROTO", "procedure",     "Procedura sicurezza fisica aree prototipo",           "ISA 8.1.2",  True),
    ("TISAX_PROTO", "record",        "Analisi rischi prototipi (veicoli/componenti)",       "ISA 8.1.3",  True),
    ("TISAX_PROTO", "procedure",     "Procedura sicurezza eventi e test drive",             "ISA 8.4.1",  False),
    ("TISAX_PROTO", "record",        "Registro incidenti relativi a prototipi",             "ISA 8.1.6",  True),
]


class Command(BaseCommand):
    help = "Load mandatory document requirements for ISO27001, NIS2, TISAX_L2, TISAX_L3, TISAX_PROTO"

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

"""Carica i documenti obbligatori per ACN_NIS2 (trasposizione italiana NIS2).

28 documenti, ciascuno mappato a un controllo ACN reale (iso_clause = external_id
completo). L'applicabilità per classificazione (essenziale/importante) è gestita a
runtime in get_required_documents_status: i documenti dei controlli 'essential'
compaiono solo dove il controllo ha un'istanza (plant essenziali).

Idempotente: get_or_create su (framework, document_type, description).
"""
from django.db import migrations

ACN_NIS2_DOCS = [
    ("policy",    "Policy di gestione del rischio di cybersecurity",        "ACN-NIS2-GV.PO-01", True),
    ("record",    "Documento ruoli e responsabilità cybersecurity",         "ACN-NIS2-GV.RR-02", True),
    ("procedure", "Programma di gestione del rischio supply chain",          "ACN-NIS2-GV.SC-01", True),
    ("record",    "Registro fornitori con prioritizzazione",                "ACN-NIS2-GV.SC-04", True),
    ("record",    "Clausole di sicurezza nei contratti con fornitori",      "ACN-NIS2-GV.SC-05", True),
    ("record",    "Inventario asset hardware",                              "ACN-NIS2-ID.AM-01", True),
    ("record",    "Inventario software, servizi e sistemi",                 "ACN-NIS2-ID.AM-02", True),
    ("record",    "Valutazione del rischio cyber (probabilità/impatto)",    "ACN-NIS2-ID.RA-05", True),
    ("record",    "Piano di trattamento del rischio",                       "ACN-NIS2-ID.RA-06", True),
    ("record",    "Registro delle vulnerabilità",                           "ACN-NIS2-ID.RA-01", True),
    ("procedure", "Piano di risposta agli incidenti",                       "ACN-NIS2-ID.IM-04", True),
    ("record",    "Mappa dei flussi di rete e dati",                        "ACN-NIS2-ID.AM-03", True),
    ("procedure", "Procedura gestione identità e accessi (IAM)",            "ACN-NIS2-PR.AA-01", True),
    ("procedure", "Procedura controllo accessi fisici",                     "ACN-NIS2-PR.AA-06", False),
    ("record",    "Piano di formazione e awareness cybersecurity",          "ACN-NIS2-PR.AT-01", True),
    ("procedure", "Procedura crittografia e protezione dati",               "ACN-NIS2-PR.DS-02", True),
    ("procedure", "Procedura backup e ripristino dati",                     "ACN-NIS2-PR.DS-11", True),
    ("procedure", "Procedura patch e aggiornamento software",               "ACN-NIS2-PR.PS-02", True),
    ("procedure", "Procedura gestione log e monitoraggio",                  "ACN-NIS2-PR.PS-04", True),
    ("procedure", "Procedura sviluppo software sicuro (SDLC)",              "ACN-NIS2-PR.PS-06", False),
    ("record",    "Piano formazione specialistica per ruoli critici",       "ACN-NIS2-PR.AT-02", True),
    ("record",    "Documentazione resilienza/ridondanza infrastruttura IT", "ACN-NIS2-PR.IR-03", True),
    ("procedure", "Procedura gestione configurazioni sicure (hardening)",   "ACN-NIS2-PR.PS-01", True),
    ("procedure", "Procedura manutenzione hardware",                        "ACN-NIS2-PR.PS-03", False),
    ("procedure", "Procedura notifica incidenti significativi (ACN/CSIRT)", "ACN-NIS2-RS.CO-02", True),
    ("record",    "Registro incidenti significativi",                       "ACN-NIS2-RS.MA-01", True),
    ("procedure", "Piano di continuità operativa e ripristino (BCP/DR)",    "ACN-NIS2-RC.RP-01", True),
    ("record",    "Piano di comunicazione durante il ripristino",           "ACN-NIS2-RC.CO-03", False),
]


def forwards(apps, schema_editor):
    RequiredDocument = apps.get_model("compliance_schedule", "RequiredDocument")
    for doc_type, description, iso_clause, mandatory in ACN_NIS2_DOCS:
        RequiredDocument.objects.get_or_create(
            framework="ACN_NIS2",
            document_type=doc_type,
            description=description,
            defaults={"iso_clause": iso_clause, "mandatory": mandatory},
        )


def backwards(apps, schema_editor):
    RequiredDocument = apps.get_model("compliance_schedule", "RequiredDocument")
    RequiredDocument.objects.filter(framework="ACN_NIS2").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("compliance_schedule", "0006_alter_requireddocument_framework"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

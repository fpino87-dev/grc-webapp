"""Allinea i documenti obbligatori TISAX_L3 al catalogo controlli VH reale.

Il seed originale citava clausole VH inesistenti. Qui, sui dati già presenti:
  - rimappa 3 documenti a controlli Very High esistenti;
  - rimuove 5 documenti privi di un controllo VH dedicato (coperti a livello L2).

Applicato via UPDATE/DELETE puntuali (non --clear) per non toccare le altre
righe. Eventuali agganci (RequiredDocumentFulfillment) verso i 5 documenti
rimossi cadono in cascata: erano requisiti non risolvibili, quindi senza aggancio
valido atteso.
"""
from django.db import migrations

# (framework, description) → nuova iso_clause
REMAPS = [
    ("TISAX_L3", "Procedura autenticazione rinforzata (MFA)", "ISA 4.1.2-VH"),
    ("TISAX_L3", "Evidenze controlli crittografici rinforzati", "ISA 5.1.2-VH"),
    ("TISAX_L3", "Procedura risposta incidenti Very High", "ISA 1.6.2-VH"),
]

# (framework, description) da rimuovere: nessun controllo VH dedicato
REMOVALS = [
    ("TISAX_L3", "Information Security Policy (ISP) — Livello VH"),
    ("TISAX_L3", "Analisi rischi approfondita Very High"),
    ("TISAX_L3", "Procedura distruzione sicura informazioni classificate"),
    ("TISAX_L3", "Procedura gestione rischi terze parti Very High"),
    ("TISAX_L3", "Accordi NDA estesi con partner OEM"),
]


def forwards(apps, schema_editor):
    RequiredDocument = apps.get_model("compliance_schedule", "RequiredDocument")
    for framework, description, new_clause in REMAPS:
        RequiredDocument.objects.filter(
            framework=framework, description=description
        ).update(iso_clause=new_clause)
    for framework, description in REMOVALS:
        RequiredDocument.objects.filter(
            framework=framework, description=description
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("compliance_schedule", "0003_requireddocumentfulfillment"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]

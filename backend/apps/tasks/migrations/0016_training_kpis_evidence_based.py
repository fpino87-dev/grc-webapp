from django.db import migrations

# Formazione a evidenze (fase 3): i KPI della formazione si calcolano dalle
# erogazioni registrate con prova e dai gruppi destinatari, non più dalle
# iscrizioni per persona né da un push esterno (KnowBe4).
#
# - phishing_click_rate: da "api" a "internal" (come la 0008 per gli altri).
# - training_completion_rate: cambia significato (copertura del personale dei
#   gruppi destinatari, non % di iscrizioni completate); nome e descrizione si
#   aggiornano solo se sono ancora quelli importati dal catalogo, per non
#   toccare definizioni personalizzate.
# Testi inlined: la migrazione non deve dipendere dal catalogo futuro.

OLD_TEXTS = {
    "training_completion_rate": (
        "Completamento formazione obbligatoria",
        "Percentuale di utenti che hanno completato la formazione obbligatoria nel periodo.",
    ),
    "phishing_click_rate": (
        "Tasso di click su phishing simulato",
        "Percentuale di utenti che cliccano sui link nelle simulazioni di phishing.",
    ),
}
NEW_TEXTS = {
    "training_completion_rate": (
        "Copertura formazione obbligatoria",
        "Percentuale del personale dei gruppi destinatari coperta da un'erogazione ancora "
        "valida dei corsi obbligatori del piano formativo dell'anno.",
    ),
    "phishing_click_rate": (
        "Tasso di click su phishing simulato",
        "Percentuale di e-mail cliccate sul totale inviato nell'ultima simulazione di "
        "phishing di ogni sito (ultimi 12 mesi).",
    ),
}


def _retext(KPIDefinition, source, target):
    for code, (old_name, old_desc) in source.items():
        new_name, new_desc = target[code]
        qs = KPIDefinition.objects.filter(kpi_code=code)
        qs.filter(name=old_name).update(name=new_name)
        qs.filter(description=old_desc).update(description=new_desc)


def forward(apps, schema_editor):
    KPIDefinition = apps.get_model("tasks", "KPIDefinition")
    KPIDefinition.objects.filter(kpi_code="phishing_click_rate", source="api").update(
        source="internal",
    )
    _retext(KPIDefinition, OLD_TEXTS, NEW_TEXTS)


def backward(apps, schema_editor):
    KPIDefinition = apps.get_model("tasks", "KPIDefinition")
    KPIDefinition.objects.filter(kpi_code="phishing_click_rate", source="internal").update(
        source="api",
    )
    _retext(KPIDefinition, NEW_TEXTS, OLD_TEXTS)


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0015_checklistrun_asset_and_more"),
    ]

    operations = [migrations.RunPython(forward, backward)]

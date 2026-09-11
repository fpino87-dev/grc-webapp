"""
La data di valutazione del fornitore diventa un dato derivato (non più inserito
a mano nell'anagrafica): data, scadenza e origine dell'ultima valutazione
registrata — questionario valutato, valutazione esistente registrata o audit
terze parti approvato.

Migrazione dati delle date inserite a mano che non corrispondono a nessun
questionario valutato né audit approvato:
  - data passata o odierna → convertita in una "valutazione esistente"
    registrata (questionario con origine "esistente", esito = livello di
    rischio indicato nell'anagrafica), così la data resta tracciata con la sua
    origine e una nota esplicativa;
  - data futura → non può essere una valutazione (probabilmente usata come
    scadenza): viene riportata nelle note del fornitore e non più usata.
Infine data/scadenza/origine vengono ricalcolate per tutti i fornitori.
Il risk_adj dei fornitori attivi viene riallineato dal ricalcolo notturno
(`recompute_expired_risk_adj_task`).
"""
import datetime

from django.db import migrations, models
from django.utils import timezone

_RISK_CLASSES = {"basso", "medio", "alto", "critico"}
_LEGACY_NOTE = (
    "Valutazione migrata automaticamente dalla «Data di valutazione» inserita a mano "
    "nell'anagrafica fornitore (campo non più editabile). Esito = livello di rischio "
    "indicato nell'anagrafica al momento della migrazione."
)


def _validity(apps):
    Config = apps.get_model("suppliers", "SupplierEvaluationConfig")
    cfg = Config.objects.first()
    if cfg is None:
        return 12, 12
    return cfg.questionnaire_validity_months, cfg.assessment_validity_months


def forwards(apps, schema_editor):
    Supplier = apps.get_model("suppliers", "Supplier")
    Questionnaire = apps.get_model("suppliers", "SupplierQuestionnaire")
    Assessment = apps.get_model("suppliers", "SupplierAssessment")

    q_months, a_months = _validity(apps)
    today = timezone.localdate()

    suppliers = Supplier._base_manager.filter(deleted_at__isnull=True)

    # 1. Date manuali non supportate da una valutazione registrata.
    for sup in suppliers.filter(evaluation_date__isnull=False):
        date = sup.evaluation_date
        backed = (
            Questionnaire._base_manager.filter(
                supplier=sup, status="risposto", evaluation_date=date, deleted_at__isnull=True,
            ).exists()
            or Assessment._base_manager.filter(
                supplier=sup, status="approvato", assessment_date=date, deleted_at__isnull=True,
            ).exists()
        )
        if backed:
            continue
        if date <= today:
            anchor = timezone.make_aware(datetime.datetime.combine(date, datetime.time.min))
            Questionnaire._base_manager.create(
                supplier=sup,
                origin="esistente",
                sent_at=anchor,
                last_sent_at=anchor,
                sent_to="",
                send_count=0,
                status="risposto",
                evaluation_date=date,
                risk_result=sup.risk_level if sup.risk_level in _RISK_CLASSES else None,
                expires_at=date + datetime.timedelta(days=q_months * 30),
                notes=_LEGACY_NOTE,
                created_by_id=sup.created_by_id,
            )
        else:
            line = (
                f"[Migrazione] La «Data di valutazione» inserita a mano era futura ({date.isoformat()}) "
                "e non è stata considerata una valutazione: se era una scadenza (es. contrattuale), "
                "riportala nel documento di contratto."
            )
            sup.notes = f"{sup.notes}\n{line}".strip() if sup.notes else line
            sup.save(update_fields=["notes"])

    # 2. Ricalcolo data/scadenza/origine (stessa logica di risk_adj._latest_evaluation).
    for sup in suppliers:
        candidates = []
        q = (
            Questionnaire._base_manager.filter(
                supplier=sup, status="risposto", evaluation_date__isnull=False, deleted_at__isnull=True,
            )
            .order_by("-evaluation_date", "-expires_at")
            .first()
        )
        if q is not None:
            expires = q.expires_at or (q.evaluation_date + datetime.timedelta(days=q_months * 30))
            candidates.append((q.evaluation_date, expires, "esistente" if q.origin == "esistente" else "questionario"))
        a = (
            Assessment._base_manager.filter(supplier=sup, status="approvato", deleted_at__isnull=True)
            .order_by("-assessment_date")
            .first()
        )
        if a is not None:
            candidates.append((a.assessment_date, a.assessment_date + datetime.timedelta(days=a_months * 30), "audit"))

        date, expires, source = max(candidates, key=lambda c: (c[0], c[1])) if candidates else (None, None, "")
        Supplier._base_manager.filter(pk=sup.pk).update(
            evaluation_date=date, evaluation_expires_at=expires, evaluation_source=source,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('suppliers', '0015_supplier_tisax_relevant'),
    ]

    operations = [
        migrations.AddField(
            model_name='supplier',
            name='evaluation_expires_at',
            field=models.DateField(blank=True, help_text="Scadenza dell'ultima valutazione: oltre questa data il fornitore va rivalutato (calcolato, read-only)", null=True),
        ),
        migrations.AddField(
            model_name='supplier',
            name='evaluation_source',
            field=models.CharField(blank=True, choices=[('questionario', 'Questionario'), ('esistente', 'Valutazione esistente registrata'), ('audit', 'Audit terze parti')], default='', help_text="Origine dell'ultima valutazione (calcolato, read-only)", max_length=15),
        ),
        migrations.AddField(
            model_name='supplierquestionnaire',
            name='origin',
            field=models.CharField(choices=[('piattaforma', 'Inviato dalla piattaforma'), ('esistente', 'Valutazione esistente registrata')], default='piattaforma', max_length=15),
        ),
        migrations.AlterField(
            model_name='supplier',
            name='evaluation_date',
            field=models.DateField(blank=True, help_text="Data dell'ultima valutazione registrata (calcolato, read-only)", null=True),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]

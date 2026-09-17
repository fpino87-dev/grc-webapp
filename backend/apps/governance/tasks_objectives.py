"""Sorveglianza automatica degli obiettivi di sicurezza (ISO 27001 §6.2).

La norma chiede obiettivi *monitorati*: senza un giro automatico, un obiettivo
fermo si scopre solo al riesame successivo — cioè quando non c'è più tempo per
rimediare.

Cadenza settimanale e non giornaliera, e per un motivo preciso: gli obiettivi
agganciati a un KPI leggono gli snapshot settimanali del motore M08, quindi
fra un lunedì e l'altro il valore non cambia. Il segnale d'allarme immediato
resta quello del KPI, che è giornaliero dove serve; qui si guarda la
traiettoria, che si muove in settimane.
"""
from celery import shared_task


# Giorni dalla scadenza entro cui avvisare chi risponde dell'obiettivo, se il
# target non è ancora raggiunto. Un mese è il minimo perché la risposta possa
# ancora essere qualcosa di più che prenderne atto.
DEADLINE_NOTICE_DAYS = 30

# Gradini della traiettoria: si notifica solo salendo di gradino.
_TRACK_SEVERITY = {"in_linea": 0, "senza_misure": 1, "a_rischio": 2, "mancato": 3}


def _worsened(previous: str, current: str) -> bool:
    return _TRACK_SEVERITY.get(current, 0) > _TRACK_SEVERITY.get(previous, 0)


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, default_retry_delay=120)
def evaluate_objectives_task(self):
    """Rivaluta gli obiettivi attivi e notifica chi deve saperlo.

    Ritorna un riepilogo di conteggi: nessun dato personale nei log (regola #11).
    """
    from django.utils import timezone

    from apps.notifications.resolver import fire_notification
    from apps.plants.services import plant_today
    from .models import SecurityObjective
    from .services import evaluate_objective, latest_objective_values

    objectives = list(
        SecurityObjective.objects.filter(status="attivo")
        .select_related("plant", "kpi_definition")
    )
    values = latest_objective_values(objectives)
    now = timezone.now()
    counts = {"valutati": 0, "a_rischio": 0, "mancati": 0, "notifiche": 0, "promemoria": 0}

    for objective in objectives:
        value, measured_on = values.get(objective.id, (None, None))
        today = plant_today(objective.plant)
        ev = evaluate_objective(objective, value=value, measured_on=measured_on, today=today)
        track = ev["track"]
        counts["valutati"] += 1
        if track == "a_rischio":
            counts["a_rischio"] += 1
        elif track == "mancato":
            counts["mancati"] += 1

        fields = ["last_track", "last_evaluated_at", "updated_at"]
        if _worsened(objective.last_track, track) and track in ("a_rischio", "mancato"):
            fire_notification(
                "objective_off_track",
                plant=objective.plant,
                context={"objective": objective, "evaluation": ev},
            )
            counts["notifiche"] += 1

        # Promemoria di avvicinamento: una volta sola, e solo se il traguardo
        # non è già stato raggiunto (un obiettivo raggiunto in anticipo non ha
        # bisogno di solleciti, ha bisogno che qualcuno lo chiuda).
        if (
            objective.deadline_notice_at is None
            and not ev["reached"]
            and 0 <= ev["days_to_target"] <= DEADLINE_NOTICE_DAYS
        ):
            fire_notification(
                "objective_deadline",
                plant=objective.plant,
                context={"objective": objective, "evaluation": ev},
            )
            objective.deadline_notice_at = now
            fields.append("deadline_notice_at")
            counts["promemoria"] += 1

        objective.last_track = track
        objective.last_evaluated_at = now
        objective.save(update_fields=fields)

    return counts

"""
Verifica periodica — il calcolo comune a tutto ciò che va riguardato a cadenza.

Rischi, controlli, piani BCP, manutenzione impianti: cambia l'oggetto e cambia
chi va avvisato, ma la domanda è sempre la stessa — «quando tocca di nuovo, e
quanto prima vado avvisato?». La risposta dipende da due cose: un'eventuale
cadenza indicata sul singolo oggetto e, in mancanza, la policy dello
scadenzario del sito (M18).

Qui sta solo quel calcolo. Il giro notturno resta in ogni modulo, perché
destinatario, priorità e testo del promemoria sono specifici del dominio e
tenerli generici li renderebbe illeggibili.
"""
import datetime


def resolve_next_date(plant, rule_type: str, base: datetime.date, months_override=None) -> datetime.date:
    """
    Prossima scadenza a partire da `base`.

    `months_override` è la cadenza in mesi indicata sul singolo oggetto: vince
    sulla policy del sito, che è il default. Senza né l'una né l'altra vale il
    default della regola nello scadenzario.
    """
    from apps.compliance_schedule.services import _add_duration, get_due_date

    if months_override:
        return _add_duration(base, int(months_override), "months")
    return get_due_date(rule_type, plant=plant, from_date=base)


def alert_window_days(plant, rule_type: str) -> int:
    """Giorni di preavviso previsti dalla policy del sito per questa regola."""
    from apps.compliance_schedule.services import get_alert_threshold

    return get_alert_threshold(rule_type, plant=plant)


def due_status(plant, rule_type: str, next_date, today: datetime.date):
    """
    `(da_segnalare, giorni_rimanenti, gia_scaduta)` per una scadenza.

    `da_segnalare` è vero dentro la finestra di preavviso della policy e da lì
    in poi: una scadenza superata resta da segnalare finché non viene chiusa.
    """
    if next_date is None:
        return False, None, False
    days_left = (next_date - today).days
    return days_left <= alert_window_days(plant, rule_type), days_left, days_left < 0

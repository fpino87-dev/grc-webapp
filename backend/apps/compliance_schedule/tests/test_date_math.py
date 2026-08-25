"""
Aritmetica delle scadenze: sommare mesi/anni a una data deve restare dentro il
calendario reale. La tabella dei giorni per mese era disallineata e produceva
date inesistenti (29 febbraio in anni non bisestili) → ValueError su tutto lo
scadenzario nei giorni di fine mese.
"""
import datetime

import pytest

from apps.compliance_schedule.services import _add_duration


@pytest.mark.parametrize(
    "base,value,unit,expected",
    [
        # Il giorno arretra all'ultimo giorno reale del mese di arrivo
        (datetime.date(2026, 8, 31), 6, "months", datetime.date(2027, 2, 28)),
        (datetime.date(2026, 8, 30), 6, "months", datetime.date(2027, 2, 28)),
        (datetime.date(2026, 8, 29), 6, "months", datetime.date(2027, 2, 28)),
        # Anno bisestile: il 29 febbraio esiste
        (datetime.date(2027, 12, 31), 2, "months", datetime.date(2028, 2, 29)),
        # Gennaio ha 31 giorni: il giorno non deve essere troncato a 28
        (datetime.date(2026, 12, 31), 1, "months", datetime.date(2027, 1, 31)),
        (datetime.date(2026, 12, 31), 3, "months", datetime.date(2027, 3, 31)),
        # Mesi da 30 giorni
        (datetime.date(2026, 1, 31), 3, "months", datetime.date(2026, 4, 30)),
        # Cambio d'anno
        (datetime.date(2026, 11, 15), 3, "months", datetime.date(2027, 2, 15)),
        # Anni
        (datetime.date(2026, 3, 10), 1, "years", datetime.date(2027, 3, 10)),
        (datetime.date(2028, 2, 29), 1, "years", datetime.date(2029, 2, 28)),
        # Giorni e settimane
        (datetime.date(2026, 8, 31), 15, "days", datetime.date(2026, 9, 15)),
        (datetime.date(2026, 8, 31), 2, "weeks", datetime.date(2026, 9, 14)),
    ],
)
def test_add_duration_stays_in_the_calendar(base, value, unit, expected):
    assert _add_duration(base, value, unit) == expected


def test_add_duration_never_raises_over_a_full_year_of_month_ends():
    """Nessuna combinazione giorno-di-partenza × mesi deve sollevare eccezioni."""
    for day_offset in range(366):
        base = datetime.date(2026, 1, 1) + datetime.timedelta(days=day_offset)
        for months in (1, 3, 6, 12, 24):
            result = _add_duration(base, months, "months")
            assert isinstance(result, datetime.date)

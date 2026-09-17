"""
Ricorrenza dei task (M08): passi di calendario veri, catena che non si spezza
quando un'occorrenza scade senza essere chiusa, nessun doppione.
"""
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="rec@test.com", email="rec@test.com", password="x"
    )


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="REC-P", name="Plant Recurrence", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


def _task(plant, recurrence, due_date, **kwargs):
    from apps.tasks.models import Task
    return Task.objects.create(
        title="Verifica periodica",
        plant=plant,
        recurrence=recurrence,
        due_date=due_date,
        **kwargs,
    )


# ── Passi di calendario ──────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "recurrence,due,expected",
    [
        ("daily", datetime.date(2026, 2, 28), datetime.date(2026, 3, 1)),
        ("weekly", datetime.date(2026, 12, 28), datetime.date(2027, 1, 4)),
        # Mesi veri: 31 gennaio + 1 mese = 28 febbraio, non "2 marzo" (30 giorni)
        ("monthly", datetime.date(2027, 1, 31), datetime.date(2027, 2, 28)),
        ("quarterly", datetime.date(2026, 11, 30), datetime.date(2027, 2, 28)),
        ("semiannual", datetime.date(2026, 8, 31), datetime.date(2027, 2, 28)),
        # Anni veri: nessuno slittamento di un giorno dopo un bisestile
        ("yearly", datetime.date(2027, 3, 1), datetime.date(2028, 3, 1)),
        ("yearly", datetime.date(2028, 2, 29), datetime.date(2029, 2, 28)),
    ],
)
@pytest.mark.django_db
def test_next_due_date_uses_calendar_steps(plant, recurrence, due, expected):
    from apps.tasks.services import next_recurrence_due_date

    task = _task(plant, recurrence, due)
    assert next_recurrence_due_date(task, today=due) == expected


@pytest.mark.django_db
def test_monthly_recurrence_does_not_drift_over_a_year(plant):
    """Con i 30 giorni fissi, 12 ripetizioni da gennaio arrivavano a dicembre
    con 5 giorni di scarto. Con i mesi veri il giorno resta lo stesso."""
    from apps.tasks.services import next_recurrence_due_date

    due = datetime.date(2026, 1, 15)
    for _ in range(12):
        task = _task(plant, "monthly", due)
        due = next_recurrence_due_date(task, today=due)
    assert due == datetime.date(2027, 1, 15)


@pytest.mark.django_db
def test_no_next_date_without_due_date_or_recurrence(plant):
    from apps.tasks.services import next_recurrence_due_date

    assert next_recurrence_due_date(_task(plant, "monthly", None)) is None
    assert next_recurrence_due_date(_task(plant, "none", datetime.date(2026, 5, 1))) is None


@pytest.mark.django_db
def test_stale_task_produces_a_single_future_occurrence(plant):
    """Un mensile fermo da tre anni non deve generare 36 arretrati: una sola
    occorrenza, nel futuro."""
    from apps.tasks.services import next_recurrence_due_date

    task = _task(plant, "monthly", timezone.localdate() - datetime.timedelta(days=1100))
    nxt = next_recurrence_due_date(task)
    assert nxt > timezone.localdate()
    assert nxt <= timezone.localdate() + datetime.timedelta(days=31)


# ── Chiusura ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_completing_a_recurring_task_spawns_the_next_one(plant, user):
    from apps.tasks.models import Task
    from apps.tasks.services import complete_task

    task = _task(plant, "semiannual", timezone.localdate() + datetime.timedelta(days=2))
    complete_task(task, user)

    child = Task.objects.get(parent_task=task)
    assert child.recurrence == "semiannual"
    assert child.due_date > timezone.localdate()
    assert child.status == "aperto"


@pytest.mark.django_db
def test_next_occurrence_keeps_the_source_link(plant, user):
    """L'occorrenza successiva non deve perdere il legame con il modulo di
    origine, altrimenti sparisce la tracciabilità della sorgente."""
    from apps.tasks.models import Task
    from apps.tasks.services import complete_task

    task = _task(
        plant, "yearly", timezone.localdate(),
        source="controllo", source_module="M03",
        source_id="11111111-1111-1111-1111-111111111111",
    )
    complete_task(task, user)

    child = Task.objects.get(parent_task=task)
    assert child.source_module == "M03"
    assert str(child.source_id) == "11111111-1111-1111-1111-111111111111"
    assert child.source == "controllo"


@pytest.mark.django_db
def test_completing_twice_does_not_duplicate_the_occurrence(plant, user):
    from apps.tasks.models import Task
    from apps.tasks.services import complete_task

    task = _task(plant, "monthly", timezone.localdate())
    complete_task(task, user)
    complete_task(task, user)
    assert Task.objects.filter(parent_task=task).count() == 1


# ── Task notturno: la catena non si spezza ───────────────────────────────────

@pytest.mark.django_db
def test_expired_recurring_task_still_spawns_the_next_one(plant):
    """Il difetto storico: un task ricorrente scaduto e mai chiuso
    interrompeva la serie in silenzio."""
    from apps.tasks.models import Task
    from apps.tasks.tasks import roll_recurring_tasks

    task = _task(plant, "yearly", timezone.localdate() - datetime.timedelta(days=10))
    roll_recurring_tasks()

    child = Task.objects.get(parent_task=task)
    assert child.due_date > timezone.localdate()
    # Il task mancato resta aperto: è la traccia del periodo saltato.
    task.refresh_from_db()
    assert task.status == "aperto"
    assert "non è stata completata" in child.notes


@pytest.mark.django_db
def test_nightly_roll_is_idempotent(plant):
    from apps.tasks.models import Task
    from apps.tasks.tasks import roll_recurring_tasks

    task = _task(plant, "quarterly", timezone.localdate() - datetime.timedelta(days=5))
    roll_recurring_tasks()
    roll_recurring_tasks()
    assert Task.objects.filter(parent_task=task).count() == 1


@pytest.mark.django_db
def test_nightly_roll_ignores_non_recurring_and_future_tasks(plant):
    from apps.tasks.models import Task
    from apps.tasks.tasks import roll_recurring_tasks

    one_off = _task(plant, "none", timezone.localdate() - datetime.timedelta(days=30))
    future = _task(plant, "monthly", timezone.localdate() + datetime.timedelta(days=5))
    roll_recurring_tasks()

    assert not Task.objects.filter(parent_task=one_off).exists()
    assert not Task.objects.filter(parent_task=future).exists()


@pytest.mark.django_db
def test_nightly_roll_ignores_completed_tasks(plant, user):
    """Un task già completato ha propagato alla chiusura: il notturno non deve
    aggiungere una seconda occorrenza."""
    from apps.tasks.models import Task
    from apps.tasks.services import complete_task
    from apps.tasks.tasks import roll_recurring_tasks

    task = _task(plant, "monthly", timezone.localdate() - datetime.timedelta(days=3))
    complete_task(task, user)
    roll_recurring_tasks()
    assert Task.objects.filter(parent_task=task).count() == 1


@pytest.mark.django_db
def test_create_task_can_open_a_recurring_series(plant):
    from apps.tasks.services import create_task

    task = create_task(
        plant=plant,
        title="Riesame semestrale",
        due_date=timezone.localdate(),
        recurrence="semiannual",
    )
    assert task.recurrence == "semiannual"


@pytest.mark.django_db
def test_deleting_the_generated_occurrence_does_not_make_it_come_back(plant):
    """Il task che tornava ogni notte.

    Chi elimina l'occorrenza generata sta dicendo che quel periodo è chiuso,
    non che ne vuole un'altra. Il controllo di idempotenza passava però dal
    manager con soft delete: l'occorrenza eliminata spariva dal controllo e il
    giro notturno ne creava una nuova, all'infinito. Per fermare la serie si
    agisce sul task ricorrente padre, non sull'occorrenza.
    """
    from apps.tasks.models import Task
    from apps.tasks.tasks import roll_recurring_tasks

    task = _task(plant, "monthly", timezone.localdate() - datetime.timedelta(days=3))
    roll_recurring_tasks()
    Task.objects.get(parent_task=task).soft_delete()

    roll_recurring_tasks()
    roll_recurring_tasks()

    assert Task.objects.all_with_deleted().filter(parent_task=task).count() == 1
    assert not Task.objects.filter(parent_task=task).exists()


@pytest.mark.django_db
def test_deleting_the_occurrence_after_completion_does_not_respawn_it(plant, user):
    """Stessa garanzia sul percorso della chiusura, non solo del giro notturno."""
    from apps.tasks.models import Task
    from apps.tasks.services import complete_task
    from apps.tasks.tasks import roll_recurring_tasks

    task = _task(plant, "monthly", timezone.localdate() - datetime.timedelta(days=3))
    complete_task(task, user)
    Task.objects.get(parent_task=task).soft_delete()

    complete_task(task, user)
    roll_recurring_tasks()

    assert Task.objects.all_with_deleted().filter(parent_task=task).count() == 1

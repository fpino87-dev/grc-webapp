"""
Riverifica periodica dei controlli (M03): cadenza dalla policy del sito o dal
singolo controllo, scadenza ricalcolata a ogni valutazione, task notturno che
marca i controlli da rivalutare.
"""
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="rev@test.com", email="rev@test.com", password="x"
    )


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        username="sysrev@test.com", email="sysrev@test.com", password="x"
    )


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="REV-P", name="Plant Review", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def control(db):
    from apps.controls.models import Control, Framework
    fw = Framework.objects.create(
        code="ISO-REV", name="ISO 27001", version="2022", published_at="2022-10-01"
    )
    return Control.objects.create(
        framework=fw,
        external_id="A.5.1",
        translations={"it": {"title": "Politiche di sicurezza"}},
        evidence_requirement={},
    )


@pytest.fixture
def instance(db, plant, control, user):
    from apps.controls.models import ControlInstance
    return ControlInstance.objects.create(
        plant=plant, control=control, owner=user, status="non_valutato"
    )


# ── Cadenza ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_default_cadence_comes_from_plant_policy(instance):
    """Senza cadenza sul controllo vale la policy del sito: control_review = 1 anno."""
    from apps.controls.services import resolve_review_due_date

    base = datetime.date(2026, 3, 10)
    assert resolve_review_due_date(instance, base=base) == datetime.date(2027, 3, 10)


@pytest.mark.django_db
def test_per_control_cadence_overrides_policy(instance):
    from apps.controls.services import resolve_review_due_date

    instance.review_frequency_months = 6
    base = datetime.date(2026, 3, 10)
    assert resolve_review_due_date(instance, base=base) == datetime.date(2026, 9, 10)


@pytest.mark.django_db
def test_semiannual_cadence_from_month_end_does_not_crash(instance):
    """31 agosto + 6 mesi = 28 febbraio, non un 29 febbraio inesistente."""
    from apps.controls.services import resolve_review_due_date

    instance.review_frequency_months = 6
    assert resolve_review_due_date(
        instance, base=datetime.date(2026, 8, 31)
    ) == datetime.date(2027, 2, 28)


@pytest.mark.django_db
def test_not_yet_evaluated_control_has_no_review_date(instance):
    from apps.controls.services import apply_review_schedule

    assert apply_review_schedule(instance) is None
    instance.refresh_from_db()
    assert instance.next_review_date is None


# ── La valutazione fa ripartire il conteggio ─────────────────────────────────

@pytest.mark.django_db
def test_evaluate_control_sets_next_review_date(instance, user):
    from apps.controls.services import evaluate_control

    evaluate_control(instance, "gap", user, note="Gap rilevato")
    instance.refresh_from_db()
    assert instance.next_review_date == timezone.localdate() + datetime.timedelta(days=365)


@pytest.mark.django_db
def test_evaluate_control_rolls_the_review_forward(instance, user):
    """Rivalutare un controllo scaduto sposta avanti la scadenza e chiude il flag."""
    from apps.controls.services import evaluate_control

    instance.status = "gap"
    instance.next_review_date = datetime.date(2026, 1, 1)
    instance.needs_revaluation = True
    instance.needs_revaluation_since = datetime.date(2026, 1, 1)
    instance.save()

    evaluate_control(instance, "gap", user, note="Rivalutato")
    instance.refresh_from_db()
    assert instance.needs_revaluation is False
    assert instance.next_review_date > timezone.localdate()


# ── Task notturno ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_nightly_task_flags_overdue_review_and_creates_task(instance, superuser):
    from apps.controls.tasks import check_control_reviews_due
    from apps.tasks.models import Task

    instance.status = "compliant"
    instance.next_review_date = timezone.localdate() - datetime.timedelta(days=3)
    instance.save()

    check_control_reviews_due()
    instance.refresh_from_db()
    assert instance.needs_revaluation is True
    assert instance.needs_revaluation_since == timezone.localdate()
    task = Task.objects.get(control_instance=instance)
    assert "SCADUTA" in task.title
    assert task.priority == "alta"


@pytest.mark.django_db
def test_nightly_task_warns_before_the_deadline(instance, superuser):
    """La soglia di preavviso della policy per control_review è 30 giorni."""
    from apps.controls.tasks import check_control_reviews_due
    from apps.tasks.models import Task

    instance.status = "compliant"
    instance.next_review_date = timezone.localdate() + datetime.timedelta(days=20)
    instance.save()

    check_control_reviews_due()
    instance.refresh_from_db()
    assert instance.needs_revaluation is True
    assert "20gg" in Task.objects.get(control_instance=instance).title


@pytest.mark.django_db
def test_nightly_task_ignores_reviews_far_away(instance, superuser):
    from apps.controls.tasks import check_control_reviews_due
    from apps.tasks.models import Task

    instance.status = "compliant"
    instance.next_review_date = timezone.localdate() + datetime.timedelta(days=200)
    instance.save()

    check_control_reviews_due()
    instance.refresh_from_db()
    assert instance.needs_revaluation is False
    assert not Task.objects.filter(control_instance=instance).exists()


@pytest.mark.django_db
def test_nightly_task_backfills_missing_review_dates(instance, superuser):
    """Un controllo valutato prima di questa funzione non ha scadenza: va
    ricostruita dall'ultima valutazione, altrimenti non verrebbe mai rivisto."""
    from apps.controls.tasks import check_control_reviews_due

    instance.status = "compliant"
    instance.last_evaluated_at = timezone.now() - datetime.timedelta(days=400)
    instance.next_review_date = None
    instance.save()

    check_control_reviews_due()
    instance.refresh_from_db()
    assert instance.next_review_date is not None
    # Valutato 400 giorni fa con cadenza annuale → riverifica già scaduta.
    assert instance.next_review_date < timezone.localdate()
    assert instance.needs_revaluation is True


@pytest.mark.django_db
def test_nightly_task_does_not_duplicate_tasks(instance, superuser):
    from apps.controls.tasks import check_control_reviews_due
    from apps.tasks.models import Task

    instance.status = "compliant"
    instance.next_review_date = timezone.localdate() - datetime.timedelta(days=3)
    instance.save()

    check_control_reviews_due()
    check_control_reviews_due()
    assert Task.objects.filter(control_instance=instance).count() == 1


@pytest.mark.django_db
def test_nightly_task_skips_excluded_controls(instance, superuser):
    from apps.controls.tasks import check_control_reviews_due

    instance.status = "compliant"
    instance.applicability = "escluso"
    instance.next_review_date = timezone.localdate() - datetime.timedelta(days=3)
    instance.save()

    check_control_reviews_due()
    instance.refresh_from_db()
    assert instance.needs_revaluation is False


@pytest.mark.django_db
def test_nightly_task_writes_audit_log(instance, superuser):
    from apps.controls.tasks import check_control_reviews_due
    from core.audit import AuditLog

    instance.status = "compliant"
    instance.next_review_date = timezone.localdate() - datetime.timedelta(days=1)
    instance.save()

    check_control_reviews_due()
    assert AuditLog.objects.filter(
        action_code="control.review_due", entity_id=instance.id
    ).exists()


# ── Scadenzario ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_control_review_appears_in_activity_schedule(instance, plant):
    from apps.compliance_schedule.services import get_activity_schedule

    instance.status = "compliant"
    instance.next_review_date = timezone.localdate() + datetime.timedelta(days=30)
    instance.save()

    labels = [a["label"] for a in get_activity_schedule(plant=plant)]
    assert "Controllo: A.5.1" in labels


@pytest.mark.django_db
def test_backfill_anchors_to_today_when_evaluation_date_is_missing(instance, superuser):
    """Controlli importati con uno stato ma senza data di valutazione: il ciclo
    parte da oggi invece di lasciarli fuori dalla riverifica per sempre."""
    from apps.controls.tasks import check_control_reviews_due

    instance.status = "compliant"
    instance.last_evaluated_at = None
    instance.next_review_date = None
    instance.save()

    check_control_reviews_due()
    instance.refresh_from_db()
    assert instance.next_review_date == timezone.localdate() + datetime.timedelta(days=365)
    assert instance.needs_revaluation is False

"""Test del comando verify_schedule (drift pianificazione Celery vs DB)."""
import pytest
from celery.schedules import crontab
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO

from apps.audit_trail.management.commands.verify_schedule import classify


def _pt(enabled=True, minute="0", hour="2", dow="*", dom="*", moy="*"):
    from django_celery_beat.models import CrontabSchedule, PeriodicTask
    cs = CrontabSchedule.objects.create(
        minute=minute, hour=hour, day_of_week=dow, day_of_month=dom, month_of_year=moy,
    )
    return PeriodicTask.objects.create(name="x", task="t", crontab=cs, enabled=enabled)


def test_classify_missing():
    status, _ = classify(crontab(hour=2, minute=0), None)
    assert status == "MISSING"


@pytest.mark.django_db
def test_classify_ok():
    pt = _pt(hour="2", minute="0")
    status, detail = classify(crontab(hour=2, minute=0), pt)
    assert status == "OK", detail


@pytest.mark.django_db
def test_classify_disabled():
    pt = _pt(enabled=False, hour="2", minute="0")
    status, _ = classify(crontab(hour=2, minute=0), pt)
    assert status == "DISABLED"


@pytest.mark.django_db
def test_classify_schedule_mismatch():
    pt = _pt(hour="3", minute="0")  # DB alle 03:00, atteso 02:00
    status, detail = classify(crontab(hour=2, minute=0), pt)
    assert status == "MISMATCH"
    assert "atteso" in detail


@pytest.mark.django_db
def test_command_report_only_does_not_raise():
    """In un DB di test senza PeriodicTask, --report-only stampa e NON solleva."""
    out = StringIO()
    call_command("verify_schedule", "--report-only", stdout=out)
    assert "Verifica pianificazione" in out.getvalue()


@pytest.mark.django_db
def test_command_raises_on_drift():
    """Senza --report-only, se ci sono voci non allineate fallisce (utile in CI)."""
    with pytest.raises(CommandError):
        call_command("verify_schedule")

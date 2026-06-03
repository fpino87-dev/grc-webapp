"""Test statico anti-drift su CELERY_BEAT_SCHEDULE (P0-2).

L'incidente originale (P0-2): una voce in `beat_schedule` con un nome di task che
non corrisponde ad alcun task registrato → il job non parte mai, in silenzio.
`verify_schedule` (management command) confronta settings vs PeriodicTask a DB:
utile a runtime, ma in CI il DB è vuoto e non può girare in modo significativo.

Questo test è la protezione **gated** complementare: valida staticamente che
ogni entry di `CELERY_BEAT_SCHEDULE` referenzi un task Celery effettivamente
registrato e abbia una `schedule` valida — fallisce alla build su un refuso o un
task rinominato/rimosso.
"""
import pytest
from django.conf import settings


def _beat():
    return getattr(settings, "CELERY_BEAT_SCHEDULE", {}) or {}


def test_beat_schedule_not_empty():
    assert _beat(), "CELERY_BEAT_SCHEDULE è vuoto: nessun job periodico definito."


def test_every_entry_has_task_and_schedule():
    for name, cfg in _beat().items():
        assert cfg.get("task"), f"voce '{name}' senza 'task'"
        assert cfg.get("schedule") is not None, f"voce '{name}' senza 'schedule'"


def test_every_task_is_registered():
    """Ogni `task` referenziato deve esistere nel registry Celery (autodiscover)."""
    from core.celery import app

    # autodiscover_tasks() è lazy (gira alla finalizzazione del worker): in pytest
    # forziamo l'import dei moduli task così il registry è popolato come a runtime.
    app.loader.import_default_modules()

    registered = set(app.tasks.keys())
    missing = {
        name: cfg["task"]
        for name, cfg in _beat().items()
        if cfg.get("task") not in registered
    }
    assert not missing, (
        "Voci di CELERY_BEAT_SCHEDULE che puntano a task NON registrati "
        f"(refuso o task rinominato/rimosso → il job non partirebbe mai): {missing}"
    )

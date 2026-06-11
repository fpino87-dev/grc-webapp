"""
Test supporto al campo `requirements` di Control (sotto-requisiti normativi
granulari, es. misure ACN NIS2): import dai JSON e localizzazione per la UI.
"""
import json
import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_load_frameworks_imports_requirements(tmp_path):
    """load_frameworks importa il campo requirements (prima veniva scartato)."""
    from apps.controls.models import Control

    data = {
        "code": "TEST_REQ", "name": "Test Req", "version": "1", "published_at": "2025-01-01",
        "domains": [],
        "controls": [{
            "external_id": "T-1",
            "translations": {"it": {"title": "T1"}},
            "requirements": [
                {"punto": "1", "applies_to": ["essential", "important"],
                 "ambiti_politiche": "a) Gestione del rischio",
                 "translations": {"it": {"text": "Elenco aggiornato dei sistemi."}}},
            ],
        }],
        "mappings": [],
    }
    f = tmp_path / "TEST_REQ.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    call_command("load_frameworks", file=str(f))

    ctrl = Control.objects.get(external_id="T-1")
    assert len(ctrl.requirements) == 1
    assert ctrl.requirements[0]["punto"] == "1"
    assert ctrl.requirements[0]["applies_to"] == ["essential", "important"]


def test_localize_requirements_picks_lang_with_fallback():
    """_localize_requirements appiattisce e localizza (fallback su 'it')."""
    from apps.controls.views.instances import _localize_requirements

    reqs = [{
        "punto": "1", "applies_to": ["important"], "ambiti_politiche": "a) X",
        "translations": {"it": {"text": "testo it"}, "en": {"text": "text en"}},
    }]
    en = _localize_requirements(reqs, "en")
    assert en[0]["text"] == "text en"
    assert en[0]["ambito"] == "a) X"
    assert en[0]["applies_to"] == ["important"]

    fr = _localize_requirements(reqs, "fr")  # lingua assente → fallback 'it'
    assert fr[0]["text"] == "testo it"

    assert _localize_requirements([], "it") == []
    assert _localize_requirements(None, "it") == []

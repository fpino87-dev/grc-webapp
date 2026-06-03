"""Regressione: valutare un controllo azzera il flag needs_revaluation.

Prima `evaluate_control` non azzerava mai il flag → un ControlInstance marcato
"da rivalutare" da un change asset restava tale a vita, anche dopo la rivalutazione.
"""
import datetime

import pytest
from django.utils import timezone


@pytest.mark.django_db
def test_evaluate_clears_needs_revaluation():
    from django.contrib.auth import get_user_model
    from apps.plants.models import Plant
    from apps.controls.models import Control, ControlInstance, Framework
    from apps.controls.services import evaluate_control

    U = get_user_model()
    user = U.objects.create_user(username="ev@test.com", email="ev@test.com", password="x")
    plant = Plant.objects.create(code="EV-P", name="P EV", country="IT",
                                 nis2_scope="non_soggetto", status="attivo")
    fw = Framework.objects.create(code="ISO27001", name="ISO", version="1",
                                  published_at=datetime.date(2024, 1, 1))
    ctrl = Control.objects.create(framework=fw, external_id="A.5.1", translations={"title": {"it": "x"}})
    ci = ControlInstance.objects.create(
        plant=plant, control=ctrl, status="compliant",
        needs_revaluation=True, needs_revaluation_since=timezone.localdate(),
    )

    # "gap" non richiede evidenze: rivalutazione che chiude il flag.
    evaluate_control(ci, "gap", user, note="rivalutato dopo change")

    ci.refresh_from_db()
    assert ci.status == "gap"
    assert ci.needs_revaluation is False
    assert ci.needs_revaluation_since is None

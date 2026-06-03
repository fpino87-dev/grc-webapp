"""Regressione: cascata register_change non deve ri-flaggare i controlli ×N processi."""
import datetime

import pytest


@pytest.fixture
def setup(db):
    from django.contrib.auth import get_user_model
    from apps.plants.models import Plant
    from apps.assets.models import AssetIT
    from apps.bia.models import CriticalProcess
    from apps.controls.models import Control, ControlInstance, Framework

    U = get_user_model()
    user = U.objects.create_user(username="cc@test.com", email="cc@test.com", password="x")
    plant = Plant.objects.create(code="CC-P", name="P CC", country="IT",
                                 nis2_scope="non_soggetto", status="attivo")
    asset = AssetIT.objects.create(plant=plant, name="Srv CC", asset_type="IT",
                                   criticality=4, created_by=user)
    # Due processi BIA legati all'asset → in passato moltiplicavano il flagging.
    p1 = CriticalProcess.objects.create(plant=plant, name="Proc1", criticality=4, status="bozza")
    p2 = CriticalProcess.objects.create(plant=plant, name="Proc2", criticality=4, status="bozza")
    asset.processes.add(p1, p2)

    fw = Framework.objects.create(code="ISO27001", name="ISO", version="1",
                                  published_at=datetime.date(2024, 1, 1))
    c1 = Control.objects.create(framework=fw, external_id="A.5.1", translations={"title": {"it": "x"}})
    c2 = Control.objects.create(framework=fw, external_id="A.5.2", translations={"title": {"it": "y"}})
    ci1 = ControlInstance.objects.create(plant=plant, control=c1, status="compliant")
    ci2 = ControlInstance.objects.create(plant=plant, control=c2, status="compliant")
    return dict(user=user, asset=asset, ci1=ci1, ci2=ci2)


@pytest.mark.django_db
def test_register_change_flags_controls_once(setup):
    from apps.assets.services import register_change

    res = register_change(setup["asset"], setup["user"], "REF-1")
    aff = res["affected"]

    assert aff["processes"] == 2
    # 2 controlli compliant → conteggio 2, NON 4 (prima ×2 processi)
    assert aff["controls"] == 2

    setup["ci1"].refresh_from_db()
    setup["ci2"].refresh_from_db()
    assert setup["ci1"].needs_revaluation is True
    assert setup["ci2"].needs_revaluation is True
    # Nessun legame asset↔controllo → fallback plant-wide.
    assert aff["controls_scope"] == "plant"
    # I controlli in gap/non_valutato non vengono toccati (esclusi dal filtro).


@pytest.mark.django_db
def test_register_change_narrows_to_linked_controls(setup):
    """P1-5: se l'asset ha controlli collegati (M2M), la cascata tocca SOLO quelli,
    non l'intera postura del plant."""
    from apps.assets.services import register_change

    # Collega solo ci1 all'asset.
    setup["ci1"].assets.add(setup["asset"])

    res = register_change(setup["asset"], setup["user"], "REF-NARROW")
    aff = res["affected"]
    assert aff["controls"] == 1
    assert aff["controls_scope"] == "asset"

    setup["ci1"].refresh_from_db()
    setup["ci2"].refresh_from_db()
    assert setup["ci1"].needs_revaluation is True
    assert setup["ci2"].needs_revaluation is False  # non collegato → non rivalutato


@pytest.mark.django_db
def test_clear_revaluation_narrowed_to_linked_controls(setup):
    """clear_revaluation_flag usa lo stesso scope del flagging: con legame attivo
    azzera solo i controlli dell'asset."""
    from apps.assets.services import clear_revaluation_flag, register_change

    setup["ci1"].assets.add(setup["asset"])
    register_change(setup["asset"], setup["user"], "REF-CLR")
    setup["ci1"].refresh_from_db()
    assert setup["ci1"].needs_revaluation is True

    clear_revaluation_flag(setup["asset"], setup["user"])
    setup["ci1"].refresh_from_db()
    assert setup["ci1"].needs_revaluation is False

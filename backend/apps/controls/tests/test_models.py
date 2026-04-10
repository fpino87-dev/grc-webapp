import pytest

from apps.controls.models import Control, ControlDomain, ControlInstance, Framework
from apps.plants.models import Plant


@pytest.mark.django_db
def test_control_domain_get_name_and_control_get_title():
    fw = Framework.objects.create(code="FW1", name="FW1", version="1.0", published_at="2024-01-01")
    dom = ControlDomain.objects.create(
        framework=fw,
        code="D1",
        translations={"it": {"name": "Dominio 1"}},
    )
    ctrl = Control.objects.create(
        framework=fw,
        domain=dom,
        external_id="C1",
        translations={"it": {"title": "Controllo 1"}},
    )
    assert dom.get_name("it") == "Dominio 1"
    assert ctrl.get_title("it") == "Controllo 1"


@pytest.mark.django_db
def test_control_instance_unique_together():
    fw = Framework.objects.create(code="FW2", name="FW2", version="1.0", published_at="2024-01-01")
    ctrl = Control.objects.create(framework=fw, external_id="C2", translations={})
    plant = Plant.objects.create(
        code="P2",
        name="Plant 2",
        country="IT",
        nis2_scope="non_soggetto",
        status="attivo",
    )
    ControlInstance.objects.create(plant=plant, control=ctrl)
    with pytest.raises(Exception):
        ControlInstance.objects.create(plant=plant, control=ctrl)


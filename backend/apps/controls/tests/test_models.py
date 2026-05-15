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
def test_control_get_title_falls_back_per_field_when_lang_partial():
    """Regression: lang esiste ma è parziale (es. solo practical_summary AI).

    Il vecchio fallback restituiva external_id; ora deve cadere su IT/EN.
    """
    fw = Framework.objects.create(code="FW_FB", name="FW", version="1.0", published_at="2024-01-01")
    ctrl = Control.objects.create(
        framework=fw,
        external_id="ISA-1.1.1",
        translations={
            "en": {"title": "EN title", "description": "EN desc"},
            "it": {"title": "Titolo IT", "description": "Desc IT"},
            "fr": {"practical_summary": "Résumé pratique"},
        },
    )
    # FR ha solo practical_summary → title deve cadere su IT (non external_id)
    assert ctrl.get_title("fr") == "Titolo IT"
    # description in FR non c'è → fallback IT
    assert ctrl.tr("description", "fr") == "Desc IT"
    # practical_summary in FR c'è → usa quello
    assert ctrl.tr("practical_summary", "fr") == "Résumé pratique"
    # campo inesistente ovunque → default
    assert ctrl.tr("guidance", "fr") == ""
    assert ctrl.tr("evidence_examples", "fr", default=[]) == []


@pytest.mark.django_db
def test_control_get_title_falls_back_to_en_when_it_missing():
    fw = Framework.objects.create(code="FW_EN", name="FW", version="1.0", published_at="2024-01-01")
    ctrl = Control.objects.create(
        framework=fw,
        external_id="X-1",
        translations={"en": {"title": "Only EN"}},
    )
    assert ctrl.get_title("fr") == "Only EN"
    assert ctrl.get_title("pl") == "Only EN"


@pytest.mark.django_db
def test_control_get_title_returns_external_id_when_no_translations():
    fw = Framework.objects.create(code="FW_NONE", name="FW", version="1.0", published_at="2024-01-01")
    ctrl = Control.objects.create(framework=fw, external_id="Y-1", translations={})
    assert ctrl.get_title("fr") == "Y-1"


@pytest.mark.django_db
def test_control_domain_get_name_falls_back_per_field():
    fw = Framework.objects.create(code="FW_D", name="FW", version="1.0", published_at="2024-01-01")
    dom = ControlDomain.objects.create(
        framework=fw,
        code="DOM",
        translations={
            "en": {"name": "EN name"},
            "it": {"name": "Nome IT"},
            "fr": {"description": "FR partial — no name"},
        },
    )
    assert dom.get_name("fr") == "Nome IT"
    assert dom.get_name("en") == "EN name"
    # nessuna chiave name in nessuna lingua → fallback al code
    dom2 = ControlDomain.objects.create(
        framework=fw, code="DOM2", translations={"fr": {"foo": "bar"}}
    )
    assert dom2.get_name("fr") == "DOM2"


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


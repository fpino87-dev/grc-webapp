"""
Export VDA ISA per TISAX L3: le coppie base L2 + estensione `-VH` devono
essere fuse in un'unica riga "L2 + L3 (VH)" che riflette il requisito
completo, con valutazione presa dalla VH (vedi dedup lato API).
"""
import pytest
from datetime import date
from django.contrib.auth import get_user_model

from apps.controls.export_engine import generate_export

User = get_user_model()


@pytest.fixture
def evaluator(db):
    return User.objects.create_user(
        username="vda_eval", email="vda_eval@test.com", password="x",
        first_name="Mario", last_name="Rossi",
    )


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="VDA-P", name="VDA Plant", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def fw_pair(db):
    from apps.controls.models import Framework
    fw_l2 = Framework.objects.create(
        code="TISAX_L2", name="TISAX L2", version="6.0", published_at=date.today(),
    )
    fw_l3 = Framework.objects.create(
        code="TISAX_L3", name="TISAX L3", version="6.0", published_at=date.today(),
    )
    return fw_l2, fw_l3


@pytest.mark.django_db
def test_l3_export_merges_base_and_vh_into_one_row(plant, fw_pair, evaluator):
    from apps.controls.models import Control, ControlInstance

    fw_l2, fw_l3 = fw_pair

    base_ctrl = Control.objects.create(
        framework=fw_l2, external_id="ISA-1.6.3",
        translations={"en": {"title": "Software whitelisting"}}, level="L2",
    )
    vh_ctrl = Control.objects.create(
        framework=fw_l3, external_id="ISA-1.6.3-VH",
        translations={"en": {
            "title": "Software whitelisting (Very High Protection)"
        }},
        level="L3",
    )

    # Base "zombie" (mai valutato dall'evaluator perché nascosto dall'API
    # quando esiste la VH che lo estende).
    ControlInstance.objects.create(
        plant=plant, control=base_ctrl,
        status="non_valutato", owner=None,
    )
    # VH è dove sta la valutazione reale.
    ControlInstance.objects.create(
        plant=plant, control=vh_ctrl,
        status="compliant", owner=evaluator,
        na_justification="conforme con monitoring continuo",
    )

    html = generate_export("TISAX_L3", plant.pk, "vda_isa", evaluator)

    # Una sola riga per ISA-1.6.3 e nessuna riga separata "-VH"
    assert html.count("<strong>ISA-1.6.3</strong>") == 1
    assert "ISA-1.6.3-VH" not in html
    assert "L2 + L3 (VH)" in html
    # Owner del VH presente
    assert "Mario Rossi" in html
    # Titolo dal base (senza appendice VH)
    assert "Software whitelisting" in html


@pytest.mark.django_db
def test_l3_export_keeps_l2_only_unchanged(plant, fw_pair, evaluator):
    """Controllo L2 senza estensione VH: una riga normale, level dal control."""
    from apps.controls.models import Control, ControlInstance

    fw_l2, _fw_l3 = fw_pair
    ctrl = Control.objects.create(
        framework=fw_l2, external_id="ISA-2.1.1",
        translations={"en": {"title": "Asset inventory"}}, level="L2",
    )
    ControlInstance.objects.create(
        plant=plant, control=ctrl, status="compliant", owner=evaluator,
    )

    html = generate_export("TISAX_L3", plant.pk, "vda_isa", evaluator)

    assert html.count("<strong>ISA-2.1.1</strong>") == 1
    assert "L2 + L3 (VH)" not in html.split("ISA-2.1.1")[1].split("</tr>")[0]

"""
Test management command: cleanup_old_tisax
"""
import pytest
from django.core.management import call_command

from apps.controls.models import Control, ControlInstance, Framework
from apps.plants.models import Plant


@pytest.fixture
def tisax_setup(db):
    """Crea Framework TISAX_L2 con controlli vecchio stile e nuovi."""
    fw = Framework.objects.create(
        code="TISAX_L2",
        name="TISAX L2 Test",
        version="5.0",
        published_at="2020-01-01",
    )
    plant = Plant.objects.create(
        code="TX-CLN",
        name="Plant Cleanup",
        country="IT",
        nis2_scope="non_soggetto",
        status="attivo",
    )
    # Vecchi controlli (formato pre-VDA-ISA-6.0)
    old_ctrl = Control.objects.create(
        framework=fw, external_id="TISAX-L2-IS-1.1", translations={}
    )
    old_inst = ControlInstance.objects.create(plant=plant, control=old_ctrl)

    # Nuovo controllo (formato ISA-X.Y.Z) — non deve essere toccato
    new_ctrl = Control.objects.create(
        framework=fw, external_id="ISA-1.1.1", translations={}
    )
    new_inst = ControlInstance.objects.create(plant=plant, control=new_ctrl)

    return {
        "fw": fw,
        "plant": plant,
        "old_ctrl": old_ctrl,
        "old_inst": old_inst,
        "new_ctrl": new_ctrl,
        "new_inst": new_inst,
    }


@pytest.mark.django_db
def test_cleanup_old_tisax_soft_deletes(tisax_setup):
    """Il comando soft-delete i controlli e le istanze con vecchio external_id."""
    call_command("cleanup_old_tisax")

    tisax_setup["old_ctrl"].refresh_from_db()
    tisax_setup["old_inst"].refresh_from_db()
    assert tisax_setup["old_ctrl"].deleted_at is not None
    assert tisax_setup["old_inst"].deleted_at is not None


@pytest.mark.django_db
def test_cleanup_preserves_new_controls(tisax_setup):
    """I controlli con nuovi external_id ISA-X.Y.Z non vengono toccati."""
    call_command("cleanup_old_tisax")

    tisax_setup["new_ctrl"].refresh_from_db()
    tisax_setup["new_inst"].refresh_from_db()
    assert tisax_setup["new_ctrl"].deleted_at is None
    assert tisax_setup["new_inst"].deleted_at is None


@pytest.mark.django_db
def test_cleanup_dry_run_makes_no_changes(tisax_setup):
    """Con --dry-run nulla viene modificato nel DB."""
    call_command("cleanup_old_tisax", dry_run=True)

    tisax_setup["old_ctrl"].refresh_from_db()
    tisax_setup["old_inst"].refresh_from_db()
    assert tisax_setup["old_ctrl"].deleted_at is None
    assert tisax_setup["old_inst"].deleted_at is None


@pytest.mark.django_db
def test_cleanup_no_tisax_framework(db):
    """Se non esistono framework TISAX, il comando termina senza errori."""
    # nessun framework nel DB — deve solo stampare il messaggio e uscire
    call_command("cleanup_old_tisax")


@pytest.mark.django_db
def test_cleanup_skips_framework_with_no_old_controls(db):
    """Se il framework esiste ma non ha controlli vecchio stile, lo skip è silenzioso."""
    fw = Framework.objects.create(
        code="TISAX_L2", name="TISAX L2", version="6.0", published_at="2023-01-01"
    )
    # Solo controllo con nuovo formato — nessun vecchio external_id
    Control.objects.create(framework=fw, external_id="ISA-1.1.1", translations={})
    # Deve completare senza errori
    call_command("cleanup_old_tisax")
    ctrl = Control.objects.get(framework=fw, external_id="ISA-1.1.1")
    assert ctrl.deleted_at is None


@pytest.mark.django_db
def test_isa_sort_key_ordering():
    """_isa_sort_key ordina correttamente i nuovi external_id ISA."""
    from apps.controls.export_engine import _isa_sort_key

    ids = ["ISA-1.10.1", "ISA-1.2.1", "ISA-1.3.4-VH", "ISA-1.3.4", "ISA-8.1.1"]
    result = sorted(ids, key=_isa_sort_key)
    assert result == ["ISA-1.2.1", "ISA-1.3.4", "ISA-1.3.4-VH", "ISA-1.10.1", "ISA-8.1.1"]

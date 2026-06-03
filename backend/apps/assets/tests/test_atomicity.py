"""Regression test atomicità (P1-2): delete_asset scollega i processi (M2M),
fa il soft-delete e scrive l'audit. Un fallimento a metà non deve lasciare un
asset con i processi già scollegati ma ancora attivo (stato incoerente)."""
from unittest import mock

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def setup(db):
    from apps.plants.models import Plant
    from apps.assets.models import AssetIT
    from apps.bia.models import CriticalProcess

    user = User.objects.create_user(username="asset_atom", email="assetatom@test.com", password="x")
    plant = Plant.objects.create(
        code="AST-ATOM", name="Plant Asset Atom", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )
    asset = AssetIT.objects.create(
        plant=plant, name="Srv Atom", asset_type="IT", criticality=3, created_by=user,
    )
    proc = CriticalProcess.objects.create(
        plant=plant, name="Proc Atom", criticality=3, status="bozza",
    )
    asset.processes.add(proc)
    return user, asset, proc


@pytest.mark.django_db
def test_delete_asset_rolls_back_on_audit_failure(setup):
    """Se l'audit fallisce dopo lo scollegamento dei processi e il soft-delete,
    l'asset deve restare attivo e con i processi ancora collegati."""
    from apps.assets.services import delete_asset

    user, asset, proc = setup

    with mock.patch("apps.assets.services.log_action", side_effect=RuntimeError("audit down")):
        with pytest.raises(RuntimeError):
            delete_asset(asset, user)

    asset.refresh_from_db()
    assert asset.deleted_at is None, "l'asset non deve risultare cancellato dopo il rollback"
    assert asset.processes.filter(pk=proc.pk).exists(), (
        "il legame col processo non deve essere rimosso se la transazione fallisce"
    )

"""Test dei comandi di portabilità e purge (compliance Data Act / GDPR)."""
import json

import pytest
from django.core.management import call_command
from django.utils import timezone


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="CMD-P", name="Cmd Plant", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.mark.django_db
def test_export_portable_data(tmp_path, plant):
    out = tmp_path / "export.json"
    call_command("export_portable_data", output=str(out))
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) > 0
    # il plant creato è presente nell'export
    assert any(rec.get("model") == "plants.plant" for rec in data)


@pytest.mark.django_db
def test_purge_dry_run_does_not_delete(plant):
    from apps.plants.models import Plant
    plant.soft_delete()
    Plant.objects.all_with_deleted().filter(pk=plant.pk).update(
        deleted_at=timezone.now() - timezone.timedelta(days=400)
    )
    call_command("purge_soft_deleted", days=365)  # dry-run di default
    assert Plant.objects.all_with_deleted().filter(pk=plant.pk).exists()


@pytest.mark.django_db
def test_purge_apply_deletes_old_soft_deleted(plant):
    from apps.plants.models import Plant
    plant.soft_delete()
    Plant.objects.all_with_deleted().filter(pk=plant.pk).update(
        deleted_at=timezone.now() - timezone.timedelta(days=400)
    )
    call_command("purge_soft_deleted", days=365, apply=True)
    assert not Plant.objects.all_with_deleted().filter(pk=plant.pk).exists()


@pytest.mark.django_db
def test_purge_keeps_recent_soft_deleted(plant):
    from apps.plants.models import Plant
    plant.soft_delete()  # deleted_at = ora (recente)
    call_command("purge_soft_deleted", days=365, apply=True)
    assert Plant.objects.all_with_deleted().filter(pk=plant.pk).exists()

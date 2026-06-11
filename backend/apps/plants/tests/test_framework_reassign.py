"""
Regressione: riassegnare a un sito un framework precedentemente rimosso non
deve dare IntegrityError.

Le ControlInstance vengono soft-deleted alla rimozione del framework, ma il
vincolo unique_together(plant, control) sul DB conta anche le righe soft-deleted.
Il guard di _create_control_instances usava il manager di default (che le
esclude) e tentava un INSERT → IntegrityError. Ora le soft-deleted vengono
riattivate.
"""
import datetime
import pytest
from django.utils import timezone
from django.urls import reverse


@pytest.fixture
def framework_iso(db):
    from apps.controls.models import Framework
    return Framework.objects.create(
        code="ISO27001", name="ISO 27001:2022", version="2022",
        published_at=datetime.date(2022, 10, 25),
    )


@pytest.fixture
def control_iso(framework_iso):
    from apps.controls.models import Control
    return Control.objects.create(
        framework=framework_iso, external_id="A.5.1",
        translations={"it": {"title": "Policy"}},
    )


@pytest.mark.django_db
def test_reassign_framework_reactivates_soft_deleted_instances(api_client, plant_nis2, control_iso, framework_iso):
    from apps.controls.models import ControlInstance
    from apps.plants.models import PlantFramework

    url = reverse("plant-framework-list")

    # 1) prima assegnazione → crea l'istanza
    r1 = api_client.post(url, {"plant": str(plant_nis2.id), "framework": str(framework_iso.id)})
    assert r1.status_code in (200, 201), r1.content
    assert ControlInstance.objects.filter(plant=plant_nis2, control=control_iso).count() == 1

    # 2) rimozione framework: soft-delete istanza + PlantFramework
    ControlInstance.objects.filter(plant=plant_nis2, control=control_iso).update(deleted_at=timezone.now())
    PlantFramework.objects.filter(plant=plant_nis2, framework=framework_iso).update(deleted_at=timezone.now())

    # 3) ri-assegnazione → NON deve dare IntegrityError, riattiva l'istanza
    r2 = api_client.post(url, {"plant": str(plant_nis2.id), "framework": str(framework_iso.id)})
    assert r2.status_code in (200, 201), r2.content

    # una sola riga (riattivata, non duplicata) e di nuovo live
    all_ci = ControlInstance.objects.all_with_deleted().filter(plant=plant_nis2, control=control_iso)
    assert all_ci.count() == 1
    assert all_ci.first().deleted_at is None

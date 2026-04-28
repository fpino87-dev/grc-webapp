import datetime

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_list_plants(api_client):
    url = reverse("plant-list")
    resp = api_client.get(url)
    assert resp.status_code in (200, 401, 403)


@pytest.mark.django_db
def test_delete_plant_soft_delete(api_client):
    from apps.plants.models import Plant

    plant = Plant.objects.create(
        code="DEL-TEST",
        name="Plant to delete",
        country="IT",
        nis2_scope="non_soggetto",
        status="attivo",
    )

    url = reverse("plant-detail", args=[plant.id])
    resp = api_client.delete(url)
    assert resp.status_code == 204

    deleted = Plant.objects.all_with_deleted().get(id=plant.id)
    assert deleted.deleted_at is not None

    list_url = reverse("plant-list")
    list_resp = api_client.get(list_url)
    assert list_resp.status_code == 200
    ids = {row["id"] for row in list_resp.data.get("results", [])}
    assert str(plant.id) not in ids


# ── newfix S10 — PlantFramework soft-delete + reattivazione ─────────────────


@pytest.fixture
def framework_iso(db):
    from apps.controls.models import Framework
    return Framework.objects.create(
        code="ISO27001", name="ISO 27001:2022", version="2022",
        published_at=datetime.date(2022, 10, 25),
    )


@pytest.mark.django_db
def test_plant_framework_delete_is_soft(api_client, plant_nis2, framework_iso):
    from apps.plants.models import PlantFramework
    pf = PlantFramework.objects.create(
        plant=plant_nis2, framework=framework_iso, active_from=datetime.date.today(),
    )
    url = reverse("plant-framework-detail", args=[pf.id])
    resp = api_client.delete(url)
    assert resp.status_code == 204

    # Hard delete vietato: il record resta nel DB con deleted_at != None.
    assert PlantFramework.objects.filter(pk=pf.pk).count() == 0
    deleted = PlantFramework.objects.all_with_deleted().get(pk=pf.pk)
    assert deleted.deleted_at is not None


@pytest.mark.django_db
def test_plant_framework_recreate_after_soft_delete_reactivates(api_client, plant_nis2, framework_iso):
    """POST con stesso (plant, framework) di un PF soft-deleted -> riattivato."""
    from apps.plants.models import PlantFramework
    pf = PlantFramework.objects.create(
        plant=plant_nis2, framework=framework_iso, active_from=datetime.date.today(),
    )
    pf.soft_delete()
    assert PlantFramework.objects.filter(pk=pf.pk).count() == 0

    url = reverse("plant-framework-list")
    resp = api_client.post(url, {
        "plant": str(plant_nis2.id),
        "framework": str(framework_iso.id),
    })
    assert resp.status_code == 201, resp.data
    # Stesso pk: e' una reattivazione, non un INSERT.
    assert resp.data["id"] == str(pf.pk)
    refreshed = PlantFramework.objects.get(pk=pf.pk)
    assert refreshed.deleted_at is None
    assert refreshed.active is True


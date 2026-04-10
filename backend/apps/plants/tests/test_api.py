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


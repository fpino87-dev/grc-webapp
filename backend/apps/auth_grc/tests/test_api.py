import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_list_user_plant_access(api_client):
    url = reverse("plant-access-list")
    resp = api_client.get(url)
    assert resp.status_code in (200, 401, 403)


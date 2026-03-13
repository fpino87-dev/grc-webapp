import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_list_plants(api_client):
    url = reverse("plant-list")
    resp = api_client.get(url)
    assert resp.status_code in (200, 401, 403)


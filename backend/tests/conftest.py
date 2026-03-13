import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def plant_nis2(db):
    from apps.plants.models import Plant

    return Plant.objects.create(
        code="NIS2-TEST",
        name="Plant NIS2",
        country="IT",
        nis2_scope="essenziale",
        status="attivo",
    )


@pytest.fixture
def plant_tisax(db):
    from apps.plants.models import Plant

    return Plant.objects.create(
        code="TISAX-TEST",
        name="Plant TISAX L3",
        country="IT",
        nis2_scope="non_soggetto",
        status="attivo",
    )


@pytest.fixture
def co_user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess

    user = User.objects.create_user(
        username="co",
        email="co@test.com",
        password="test",
    )
    UserPlantAccess.objects.create(
        user=user,
        role=GrcRole.COMPLIANCE_OFFICER,
        scope_type="org",
    )
    return user


@pytest.fixture
def api_client(co_user):
    client = APIClient()
    client.force_authenticate(user=co_user)
    return client


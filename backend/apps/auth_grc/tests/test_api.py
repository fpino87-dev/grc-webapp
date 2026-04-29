import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient


User = get_user_model()


@pytest.mark.django_db
def test_list_user_plant_access(api_client):
    url = reverse("plant-access-list")
    resp = api_client.get(url)
    assert resp.status_code in (200, 401, 403)


# newfix F2 — assegnazione/modifica/revoca di UserPlantAccess deve produrre
# un audit log dedicato (ISO 27001 A.9.2.2 + A.9.4.4).
@pytest.fixture
def admin_client(db):
    admin = User.objects.create_superuser(
        username="superadmin@test.com",
        email="superadmin@test.com",
        password="x",
    )
    client = APIClient()
    client.force_authenticate(user=admin)
    return client, admin


@pytest.fixture
def target_user(db):
    return User.objects.create_user(
        username="target@test.com",
        email="target@test.com",
        password="x",
    )


@pytest.mark.django_db
def test_create_user_plant_access_audits_grant(admin_client, target_user, plant_nis2):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    from core.audit import AuditLog

    client, _ = admin_client
    url = reverse("plant-access-list")
    resp = client.post(
        url,
        data={
            "user": target_user.pk,
            "role": GrcRole.RISK_MANAGER,
            "scope_type": "single_plant",
            "scope_plants": [str(plant_nis2.pk)],
        },
        format="json",
    )
    assert resp.status_code in (200, 201), resp.content
    access = UserPlantAccess.objects.get(user=target_user)
    audit = AuditLog.objects.filter(
        action_code="auth.access.granted", entity_id=access.pk,
    ).first()
    assert audit is not None
    assert audit.payload["role"] == GrcRole.RISK_MANAGER
    assert audit.payload["scope_type"] == "single_plant"
    assert str(plant_nis2.pk) in audit.payload["scope_plant_ids"]


@pytest.mark.django_db
def test_destroy_user_plant_access_audits_revoke(admin_client, target_user, plant_nis2):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    from core.audit import AuditLog

    access = UserPlantAccess.objects.create(
        user=target_user, role=GrcRole.PLANT_MANAGER, scope_type="single_plant",
    )
    access.scope_plants.add(plant_nis2)

    client, _ = admin_client
    url = reverse("plant-access-detail", args=[access.pk])
    resp = client.delete(url)
    assert resp.status_code == 204
    audit = AuditLog.objects.filter(
        action_code="auth.access.revoked", entity_id=access.pk,
    ).first()
    assert audit is not None
    assert audit.payload["role"] == GrcRole.PLANT_MANAGER


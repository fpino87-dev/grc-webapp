"""Review prod-readiness M04 (2026-06-13).

NetworkZone e AssetDependency erano eliminati con HARD delete senza audit
(viewset col destroy di default). Ora soft delete + audit via SoftDeleteAuditMixin.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.auth_grc.models import GrcRole, UserPlantAccess

User = get_user_model()


@pytest.fixture
def admin_client(db):
    u = User.objects.create_user(username="m4admin", email="m4@a.test", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="M4P", name="M4 Plant", country="IT",
                                nis2_scope="importante", status="attivo")


@pytest.mark.django_db
def test_network_zone_delete_is_soft_and_audited(admin_client, plant):
    from apps.assets.models import NetworkZone
    from core.audit import AuditLog
    z = NetworkZone.objects.create(plant=plant, name="DMZ-1", zone_type="DMZ")
    resp = admin_client.delete(f"/api/v1/assets/network-zones/{z.id}/")
    assert resp.status_code == 204
    z.refresh_from_db()
    assert z.deleted_at is not None
    assert not NetworkZone.objects.filter(pk=z.id).exists()
    assert AuditLog.objects.filter(action_code="assets.network_zone.delete").exists()


@pytest.mark.django_db
def test_asset_dependency_delete_is_soft_and_audited(admin_client, plant):
    from apps.assets.models import AssetDependency, AssetIT
    from core.audit import AuditLog
    a = AssetIT.objects.create(plant=plant, name="A", asset_type="IT")
    b = AssetIT.objects.create(plant=plant, name="B", asset_type="IT")
    dep = AssetDependency.objects.create(from_asset=a, to_asset=b, dep_type="dipende_da")
    resp = admin_client.delete(f"/api/v1/assets/dependencies/{dep.id}/")
    assert resp.status_code == 204
    dep.refresh_from_db()
    assert dep.deleted_at is not None
    assert AuditLog.objects.filter(action_code="assets.asset_dependency.delete").exists()


@pytest.mark.django_db
def test_asset_create_sets_created_by(admin_client, plant):
    from apps.assets.models import AssetIT
    resp = admin_client.post("/api/v1/assets/it/",
                             {"plant": str(plant.id), "name": "Srv1", "criticality": 3},
                             format="json")
    assert resp.status_code == 201, resp.data
    a = AssetIT.objects.get(pk=resp.data["id"])
    assert a.created_by_id is not None

"""Review prod-readiness M03 (pass leggero, 2026-06-13).

Il default destroy di ControlViewSet faceva HARD delete del Control →
CASCADE (FK on_delete=CASCADE) su tutte le ControlInstance valutate, perdita
dati su tutti i siti. Ora soft delete + audit: le istanze sopravvivono.
"""
import datetime

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.auth_grc.models import GrcRole, UserPlantAccess

User = get_user_model()


@pytest.fixture
def admin_client(db):
    u = User.objects.create_user(username="m3admin", email="m3@a.test", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.mark.django_db
def test_control_delete_is_soft_and_does_not_cascade_instances(admin_client):
    from apps.controls.models import Control, ControlInstance, Framework
    from apps.plants.models import Plant
    from core.audit import AuditLog

    fw = Framework.objects.create(code="M3FW", name="M3 FW", version="1", published_at=datetime.date.today())
    ctrl = Control.objects.create(framework=fw, external_id="M3.1", translations={"it": {"title": "T"}})
    plant = Plant.objects.create(code="M3P", name="M3 Plant", country="IT", nis2_scope="importante", status="attivo")
    inst = ControlInstance.objects.create(plant=plant, control=ctrl, status="compliant")

    resp = admin_client.delete(f"/api/v1/controls/controls/{ctrl.id}/")
    assert resp.status_code == 204

    # Control soft-deleted, NON sparito dal DB
    assert Control.objects.all_with_deleted().filter(pk=ctrl.id, deleted_at__isnull=False).exists()
    # L'istanza valutata sopravvive (niente cascade hard delete)
    assert ControlInstance.objects.all_with_deleted().filter(pk=inst.id).exists()
    assert AuditLog.objects.filter(action_code="controls.control.delete").exists()

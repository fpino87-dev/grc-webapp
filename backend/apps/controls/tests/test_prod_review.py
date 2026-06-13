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
def test_control_with_evaluations_is_blocked_not_deleted(admin_client):
    """Guard: un controllo con valutazioni NON si elimina (niente catena rotta
    né perdita dati). Si gestisce via load_frameworks."""
    from apps.controls.models import Control, ControlInstance, Framework
    from apps.plants.models import Plant

    fw = Framework.objects.create(code="M3FW", name="M3 FW", version="1", published_at=datetime.date.today())
    ctrl = Control.objects.create(framework=fw, external_id="M3.1", translations={"it": {"title": "T"}})
    plant = Plant.objects.create(code="M3P", name="M3 Plant", country="IT", nis2_scope="importante", status="attivo")
    inst = ControlInstance.objects.create(plant=plant, control=ctrl, status="compliant")

    resp = admin_client.delete(f"/api/v1/controls/controls/{ctrl.id}/")
    assert resp.status_code == 400
    # Controllo e istanza intatti (niente hard cascade, niente soft delete)
    assert Control.objects.filter(pk=ctrl.id, deleted_at__isnull=True).exists()
    assert ControlInstance.objects.filter(pk=inst.id, deleted_at__isnull=True).exists()


@pytest.mark.django_db
def test_control_without_evaluations_is_soft_deleted(admin_client):
    from apps.controls.models import Control, Framework
    from core.audit import AuditLog

    fw = Framework.objects.create(code="M3FW2", name="M3 FW2", version="1", published_at=datetime.date.today())
    ctrl = Control.objects.create(framework=fw, external_id="M3.2", translations={"it": {"title": "T"}})

    resp = admin_client.delete(f"/api/v1/controls/controls/{ctrl.id}/")
    assert resp.status_code == 204
    assert Control.objects.all_with_deleted().filter(pk=ctrl.id, deleted_at__isnull=False).exists()
    assert AuditLog.objects.filter(action_code="controls.control.delete").exists()

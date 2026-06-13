"""Review prod-readiness M05 (2026-06-13).

TreatmentOption e soprattutto RiskDecision (record governance L3 — chi ha deciso
cosa sul rischio) erano eliminati con HARD delete senza audit. Ora soft delete
+ audit via SoftDeleteAuditMixin.
"""
import datetime

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.auth_grc.models import GrcRole, UserPlantAccess

User = get_user_model()


@pytest.fixture
def admin_client(db):
    u = User.objects.create_user(username="m5admin", email="m5@a.test", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    c = APIClient()
    c.force_authenticate(user=u)
    return u, _auth(u)


def _auth(u):
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.fixture
def process(db):
    from apps.bia.models import CriticalProcess
    from apps.plants.models import Plant
    plant = Plant.objects.create(code="M5P", name="M5 Plant", country="IT",
                                 nis2_scope="importante", status="attivo")
    return CriticalProcess.objects.create(
        plant=plant, name="Proc", status="bozza",
        downtime_cost_hour=100, fatturato_esposto_anno=1000,
        mtpd_hours=48, mbco_pct=50, rto_target_hours=24, rpo_target_hours=12,
    )


@pytest.mark.django_db
def test_risk_decision_delete_is_soft_and_audited(admin_client, process):
    from apps.bia.models import RiskDecision
    from core.audit import AuditLog
    user, client = admin_client
    d = RiskDecision.objects.create(
        process=process, decision="accettare", rationale="ok",
        decided_by=user, review_by=datetime.date.today() + datetime.timedelta(days=365),
    )
    resp = client.delete(f"/api/v1/bia/risk-decisions/{d.id}/")
    assert resp.status_code == 204
    d.refresh_from_db()
    assert d.deleted_at is not None
    assert not RiskDecision.objects.filter(pk=d.id).exists()
    assert AuditLog.objects.filter(action_code="bia.risk_decision.delete").exists()


@pytest.mark.django_db
def test_treatment_option_delete_is_soft_and_audited(admin_client, process):
    from apps.bia.models import TreatmentOption
    from core.audit import AuditLog
    _, client = admin_client
    t = TreatmentOption.objects.create(process=process, title="Backup", cost_implementation=1000,
                                       cost_annual=100, ale_reduction_pct=0.3)
    resp = client.delete(f"/api/v1/bia/treatment-options/{t.id}/")
    assert resp.status_code == 204
    t.refresh_from_db()
    assert t.deleted_at is not None
    assert AuditLog.objects.filter(action_code="bia.treatment_option.delete").exists()

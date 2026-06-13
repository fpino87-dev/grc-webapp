"""Review prod-readiness M06 (2026-06-13).

RiskDimension e RiskAppetitePolicy erano eliminate con HARD delete senza audit.
La policy di appetito governa la soglia di accettazione del rischio: ogni
modifica/eliminazione va tracciata.
"""
import datetime

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.auth_grc.models import GrcRole, UserPlantAccess

User = get_user_model()


@pytest.fixture
def admin_client(db):
    u = User.objects.create_user(username="m6admin", email="m6@a.test", password="x")
    u.is_superuser = True
    u.is_staff = True
    u.save()
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="M6P", name="M6 Plant", country="IT",
                                nis2_scope="importante", status="attivo")


@pytest.mark.django_db
def test_risk_dimension_delete_is_soft_and_audited(admin_client, plant):
    from apps.risk.models import RiskAssessment, RiskDimension
    from core.audit import AuditLog
    a = RiskAssessment.objects.create(
        plant=plant, name="R", assessment_type="IT", threat_category="malware_ransomware",
        probability=3, impact=4, status="bozza",
    )
    dim = RiskDimension.objects.create(assessment=a, dimension_code="confidentiality", value=3)
    resp = admin_client.delete(f"/api/v1/risk/dimensions/{dim.id}/")
    assert resp.status_code == 204
    dim.refresh_from_db()
    assert dim.deleted_at is not None
    assert AuditLog.objects.filter(action_code="risk.dimension.delete").exists()


@pytest.mark.django_db
def test_appetite_policy_delete_and_update_audited(admin_client, plant):
    from apps.risk.models import RiskAppetitePolicy
    from core.audit import AuditLog
    p = RiskAppetitePolicy.objects.create(
        plant=plant, framework_code="ISO27001", max_acceptable_score=10,
        valid_from=datetime.date.today(),
    )
    # update → audit (modifica soglia accettazione rischio)
    resp = admin_client.patch(f"/api/v1/risk/appetite-policies/{p.id}/",
                              {"max_acceptable_score": 14}, format="json")
    assert resp.status_code == 200
    assert AuditLog.objects.filter(action_code="risk.appetite_policy.update").exists()
    # delete → soft + audit
    resp = admin_client.delete(f"/api/v1/risk/appetite-policies/{p.id}/")
    assert resp.status_code == 204
    p.refresh_from_db()
    assert p.deleted_at is not None
    assert AuditLog.objects.filter(action_code="risk.appetite_policy.delete").exists()

"""Test della review prod-readiness M00 (2026-06-13).

Copre i fix: soft delete + audit su committee / meeting / document-workflow-policy
(prima hard delete senza audit), guard sul parametro `days`, e read_only su
created_by del RoleAssignment.
"""
import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_ASSIGNMENTS = "/api/v1/governance/role-assignments/"
URL_COMMITTEES = "/api/v1/governance/committees/"
URL_MEETINGS = "/api/v1/governance/meetings/"
URL_DWP = "/api/v1/governance/document-workflow-policies/"


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="gov_pr", email="govpr@test.com", password="test")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.mark.django_db
def test_committee_delete_is_soft_and_audited(client):
    from apps.governance.models import SecurityCommittee
    from core.audit import AuditLog

    c = SecurityCommittee.objects.create(
        name="Comitato Centrale", committee_type="centrale", frequency="trimestrale",
    )
    resp = client.delete(f"{URL_COMMITTEES}{c.id}/")
    assert resp.status_code == 204

    c.refresh_from_db()
    assert c.deleted_at is not None  # soft delete, non sparito dal DB
    assert not SecurityCommittee.objects.filter(pk=c.id).exists()  # fuori dal manager default
    assert AuditLog.objects.filter(action_code="governance.security_committee.delete").exists()


@pytest.mark.django_db
def test_document_workflow_policy_delete_is_soft_and_audited(client):
    from apps.governance.models import DocumentWorkflowPolicy
    from core.audit import AuditLog

    p = DocumentWorkflowPolicy.objects.create(
        document_type="policy", scope_type="org", approve_roles=["ciso"],
    )
    resp = client.delete(f"{URL_DWP}{p.id}/")
    assert resp.status_code == 204

    p.refresh_from_db()
    assert p.deleted_at is not None
    assert AuditLog.objects.filter(action_code="governance.document_workflow_policy.delete").exists()


@pytest.mark.django_db
def test_document_workflow_policy_create_update_audited(client):
    from core.audit import AuditLog

    resp = client.post(
        URL_DWP,
        {"document_type": "procedura", "scope_type": "org", "approve_roles": ["ciso"]},
        format="json",
    )
    assert resp.status_code == 201
    pid = resp.data["id"]
    assert AuditLog.objects.filter(action_code="governance.document_workflow_policy.create").exists()

    resp = client.patch(f"{URL_DWP}{pid}/", {"approve_roles": ["compliance_officer"]}, format="json")
    assert resp.status_code == 200
    assert AuditLog.objects.filter(action_code="governance.document_workflow_policy.update").exists()


@pytest.mark.django_db
def test_in_scadenza_days_param_robust(client):
    # un valore non intero non deve più causare 500
    resp = client.get(f"{URL_ASSIGNMENTS}in-scadenza/?days=abc")
    assert resp.status_code == 200
    resp = client.get(f"{URL_ASSIGNMENTS}in-scadenza/?days=30")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_role_assignment_created_by_is_read_only(client, user):
    """Un client non può impostare created_by: lo fissa perform_create."""
    from apps.governance.models import NormativeRole, RoleAssignment

    other = User.objects.create_user(username="other_pr", email="other@test.com", password="test")
    resp = client.post(
        URL_ASSIGNMENTS,
        {
            "user": str(user.id),
            "role": NormativeRole.DPO,
            "scope_type": "org",
            "valid_from": str(timezone.localdate()),
            "created_by": str(other.id),  # tentativo di spoofing → ignorato
        },
        format="json",
    )
    assert resp.status_code == 201
    ra = RoleAssignment.objects.get(pk=resp.data["id"])
    assert ra.created_by_id == user.id

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
def test_role_list_scoped_by_plant_access(db):
    """D1: un utente scoped a un sito vede le assegnazioni org + del proprio
    sito, NON i titolari (con PII) di altri siti."""
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    from apps.plants.models import BusinessUnit, Plant
    from apps.governance.models import RoleAssignment, NormativeRole

    bu_a = BusinessUnit.objects.create(code="GBA", name="BU GA")
    bu_b = BusinessUnit.objects.create(code="GBB", name="BU GB")
    pa = Plant.objects.create(code="GPA", name="Plant GPA", country="IT", bu=bu_a,
                              nis2_scope="importante", status="attivo")
    pb = Plant.objects.create(code="GPB", name="Plant GPB", country="IT", bu=bu_b,
                              nis2_scope="importante", status="attivo")

    auditor = User.objects.create_user(username="ext_aud", email="ext@test.com", password="test")
    acc = UserPlantAccess.objects.create(
        user=auditor, role=GrcRole.EXTERNAL_AUDITOR, scope_type="single_plant",
    )
    acc.scope_plants.add(pa)

    today = timezone.localdate()
    RoleAssignment.objects.create(user=auditor, role=NormativeRole.CISO, scope_type="org", valid_from=today)
    RoleAssignment.objects.create(user=auditor, role=NormativeRole.PLANT_MANAGER,
                                  scope_type="plant", scope_id=pa.id, valid_from=today)
    RoleAssignment.objects.create(user=auditor, role=NormativeRole.PLANT_MANAGER,
                                  scope_type="plant", scope_id=pb.id, valid_from=today)

    c = APIClient()
    c.force_authenticate(user=auditor)
    resp = c.get(URL_ASSIGNMENTS)
    assert resp.status_code == 200
    rows = resp.data["results"] if isinstance(resp.data, dict) else resp.data
    pairs = {(r["scope_type"], str(r.get("scope_id"))) for r in rows}
    assert any(st == "org" for st, _ in pairs)
    assert ("plant", str(pa.id)) in pairs
    assert ("plant", str(pb.id)) not in pairs  # sito non accessibile → nascosto


@pytest.mark.django_db
def test_scope_code_name_structured(client, user):
    """D2: il serializer espone code/name strutturati (no più label IT hardcoded)."""
    from apps.plants.models import BusinessUnit, Plant
    from apps.governance.models import RoleAssignment, NormativeRole

    bu = BusinessUnit.objects.create(code="GBX", name="BU GX")
    p = Plant.objects.create(code="GPX", name="Plant GPX", country="IT", bu=bu,
                             nis2_scope="importante", status="attivo")
    RoleAssignment.objects.create(user=user, role=NormativeRole.PLANT_MANAGER,
                                  scope_type="plant", scope_id=p.id, valid_from=timezone.localdate())

    resp = client.get(URL_ASSIGNMENTS)
    assert resp.status_code == 200
    rows = resp.data["results"] if isinstance(resp.data, dict) else resp.data
    plant_rows = [r for r in rows if r["scope_type"] == "plant"]
    assert plant_rows, "nessuna riga plant"
    row = plant_rows[0]
    assert row["scope_code"] == "GPX"
    assert row["scope_name"] == "Plant GPX"
    assert "scope_label" not in row


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

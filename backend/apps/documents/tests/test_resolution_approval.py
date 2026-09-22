"""Approvazione per delibera dell'organo e approvazione dell'owner (M07)."""
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def user(db):
    return User.objects.create_user(username="segr", email="segr@x.it", password="x")


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="RES-P", name="Plant Res", country="IT",
                                nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def cda(db):
    from apps.governance.models import SecurityCommittee
    return SecurityCommittee.objects.create(name="CdA", committee_type="cda")


@pytest.fixture
def policy_document(db, plant, user):
    from apps.documents.models import Document
    return Document.objects.create(
        title="Politica sicurezza", category="politica", document_type="policy",
        status="revisione", plant=plant, is_mandatory=True, created_by=user,
    )


@pytest.fixture
def body_policy(db, cda):
    """Le politiche entrano in vigore solo con delibera del CdA."""
    from apps.governance.models import DocumentWorkflowPolicy, NormativeRole
    return DocumentWorkflowPolicy.objects.create(
        document_type="policy", scope_type="org",
        submit_roles=[NormativeRole.COMPLIANCE_OFFICER],
        review_roles=[NormativeRole.CISO],
        approve_roles=[NormativeRole.CISO],
        requires_body_resolution=True,
        approval_body=cda,
    )


def test_in_app_approval_refused_when_body_resolution_required(policy_document, body_policy, user):
    from apps.documents.services import approve_document

    with pytest.raises(ValidationError) as exc:
        approve_document(policy_document, user)
    assert "delibera" in str(exc.value).lower()
    policy_document.refresh_from_db()
    assert policy_document.status == "revisione"


def test_resolution_approval_records_details(policy_document, body_policy, cda, user):
    from apps.documents.models import DocumentApproval
    from apps.documents.services import approve_document

    delibera = timezone.localdate() - datetime.timedelta(days=2)
    approve_document(
        policy_document, user, notes="ok",
        mode="delibera", resolution_ref="4/2026", resolution_date=delibera,
    )

    policy_document.refresh_from_db()
    record = DocumentApproval.objects.get(document=policy_document, action="approve")
    assert policy_document.status == "approvato"
    assert record.approval_mode == "delibera"
    assert record.resolution_ref == "4/2026"
    assert record.resolution_date == delibera
    # l'organo arriva dalla policy quando non è indicato esplicitamente
    assert record.governing_body_id == cda.pk
    # entrata in vigore = giorno della delibera, non della registrazione
    assert policy_document.approved_at.date() == delibera


def test_resolution_requires_ref_and_date(policy_document, body_policy, user):
    from apps.documents.services import approve_document

    with pytest.raises(ValidationError):
        approve_document(policy_document, user, mode="delibera", resolution_ref="", resolution_date=None)
    with pytest.raises(ValidationError):
        approve_document(policy_document, user, mode="delibera", resolution_ref="4/2026",
                         resolution_date=timezone.localdate() + datetime.timedelta(days=1))


def test_resolution_approves_document_still_in_draft(plant, body_policy, user):
    """La delibera dell'organo manda in vigore anche un documento in bozza."""
    from apps.documents.models import Document
    from apps.documents.services import approve_document

    doc = Document.objects.create(
        title="Politica accessi", category="politica", document_type="policy",
        status="bozza", plant=plant, is_mandatory=True, created_by=user,
    )
    approve_document(doc, user, mode="delibera", resolution_ref="5/2026",
                     resolution_date=timezone.localdate())
    doc.refresh_from_db()
    assert doc.status == "approvato"


def test_resolution_refused_on_archived_document(policy_document, body_policy, user):
    from apps.documents.services import approve_document

    policy_document.status = "archiviato"
    policy_document.save(update_fields=["status"])
    with pytest.raises(ValidationError):
        approve_document(policy_document, user, mode="delibera", resolution_ref="6/2026",
                         resolution_date=timezone.localdate())


def test_owner_can_approve_when_policy_allows(plant, user):
    """Contratti e NDA: li chiude il loro titolare, senza nomina normativa."""
    from apps.documents.models import Document
    from apps.governance.models import DocumentWorkflowPolicy, NormativeRole
    from apps.governance.services import user_has_document_permission

    DocumentWorkflowPolicy.objects.create(
        document_type="contratto", scope_type="org",
        approve_roles=[NormativeRole.CISO], owner_can_approve=True,
    )
    doc = Document.objects.create(
        title="NDA fornitore", category="contratto", document_type="contratto",
        status="revisione", plant=plant, owner=user, created_by=user,
    )
    assert user_has_document_permission(user, doc, action="approve") is True

    other = User.objects.create_user(username="altro", email="altro@x.it", password="x")
    assert user_has_document_permission(other, doc, action="approve") is False


def test_only_governance_registers_resolution(policy_document, body_policy, plant):
    """La delibera si trascrive da governance, non da chi ha solo scrittura."""
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    from apps.documents.services import can_register_resolution
    from rest_framework.test import APIClient

    control_owner = User.objects.create_user(username="co_doc", email="co@x.it", password="x")
    UserPlantAccess.objects.create(user=control_owner, role=GrcRole.CONTROL_OWNER, scope_type="org")
    compliance = User.objects.create_user(username="comp", email="comp@x.it", password="x")
    UserPlantAccess.objects.create(user=compliance, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")

    assert can_register_resolution(control_owner) is False
    assert can_register_resolution(compliance) is True

    client = APIClient()
    client.force_authenticate(user=control_owner)
    resp = client.post(
        f"/api/v1/documents/documents/{policy_document.id}/approve/",
        {"mode": "delibera", "resolution_ref": "7/2026", "resolution_date": str(timezone.localdate())},
        format="json",
    )
    assert resp.status_code == 403
    policy_document.refresh_from_db()
    assert policy_document.status == "revisione"

    client.force_authenticate(user=compliance)
    resp = client.post(
        f"/api/v1/documents/documents/{policy_document.id}/approve/",
        {"mode": "delibera", "resolution_ref": "7/2026", "resolution_date": str(timezone.localdate())},
        format="json",
    )
    assert resp.status_code == 200, resp.data
    assert resp.data["last_approval"]["mode"] == "delibera"
    assert resp.data["last_approval"]["resolution_ref"] == "7/2026"
    assert resp.data["last_approval"]["governing_body"] == "CdA"

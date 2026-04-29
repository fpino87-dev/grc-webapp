"""Test della validazione automatica dell'AuditPrep."""
from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


URL_PREPS = "/api/v1/audit-prep/audit-preps/"


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(
        username="autoval", email="autoval@test.com", password="x"
    )
    UserPlantAccess.objects.create(
        user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org",
    )
    return u


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="AV-P", name="Plant AV", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def framework(db):
    from apps.controls.models import Framework
    return Framework.objects.create(
        code="ISO-AV", name="ISO 27001 AV", version="2022",
        published_at=date.today(),
    )


@pytest.fixture
def control_instance(db, plant, framework):
    from apps.controls.models import Control, ControlDomain, ControlInstance
    dom = ControlDomain.objects.create(
        framework=framework, code="AV.1",
        translations={"it": {"name": "Dom"}}, order=1,
    )
    ctrl = Control.objects.create(
        framework=framework, domain=dom, external_id="AV.1.1",
        translations={"it": {"name": "Ctrl", "description": "D"}},
        level="L2", evidence_requirement={}, control_category="technical",
    )
    return ControlInstance.objects.create(
        plant=plant, control=ctrl, status="non_valutato",
    )


@pytest.fixture
def audit_prep(db, plant, framework, user):
    from apps.audit_prep.models import AuditPrep
    return AuditPrep.objects.create(
        plant=plant, framework=framework,
        title="Audit AV Q1", audit_date=date.today(),
        status="in_corso", created_by=user,
    )


def _make_evidence_item(prep, control_instance, user):
    from apps.audit_prep.models import EvidenceItem
    return EvidenceItem.objects.create(
        audit_prep=prep,
        control_instance=control_instance,
        description=f"{control_instance.control.external_id} — evidenza",
        status="mancante",
        created_by=user,
    )


@pytest.mark.django_db
def test_auto_validate_marks_presente_when_evidence_and_doc_valid(
    client, audit_prep, control_instance, user, plant,
):
    """ci con evidenza valida + documento approvato + nessun major -> presente."""
    from apps.documents.models import Document, Evidence

    item = _make_evidence_item(audit_prep, control_instance, user)

    ev = Evidence.objects.create(
        title="Screenshot config",
        evidence_type="screenshot",
        valid_until=date.today() + timedelta(days=30),
        plant=plant,
    )
    control_instance.evidences.add(ev)

    doc = Document.objects.create(
        title="Policy AV", category="policy", document_type="policy",
        plant=plant, status="approvato",
        expiry_date=date.today() + timedelta(days=180),
    )
    doc.control_refs.add(control_instance)

    resp = client.post(f"{URL_PREPS}{audit_prep.id}/auto-validate/")
    assert resp.status_code == 200, resp.json()
    data = resp.json()
    assert data["evaluated"] == 1
    assert data["presente"] == 1
    assert data["findings_created"] == 0

    item.refresh_from_db()
    assert item.status == "presente"
    assert "[Auto-validate" in item.notes


@pytest.mark.django_db
def test_auto_validate_marks_scaduto_and_creates_finding(
    client, audit_prep, control_instance, user, plant,
):
    """Evidenza scaduta -> status="scaduto" + minor_nc auto-generato."""
    from apps.audit_prep.models import AuditFinding
    from apps.documents.models import Evidence

    item = _make_evidence_item(audit_prep, control_instance, user)
    ev = Evidence.objects.create(
        title="Cert scaduto", evidence_type="certificato",
        valid_until=date.today() - timedelta(days=10),
        plant=plant,
    )
    control_instance.evidences.add(ev)

    resp = client.post(f"{URL_PREPS}{audit_prep.id}/auto-validate/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["scaduto"] == 1
    assert data["findings_created"] == 1

    item.refresh_from_db()
    assert item.status == "scaduto"

    finding = AuditFinding.objects.get(
        audit_prep=audit_prep, control_instance=control_instance,
    )
    assert finding.finding_type == "minor_nc"
    assert finding.auto_generated is True
    assert finding.status == "open"
    assert "scaduta" in finding.title.lower()


@pytest.mark.django_db
def test_auto_validate_marks_mancante_and_creates_finding(
    client, audit_prep, control_instance, user,
):
    """Nessuna evidenza ne' documento -> mancante + minor_nc."""
    from apps.audit_prep.models import AuditFinding

    item = _make_evidence_item(audit_prep, control_instance, user)

    resp = client.post(f"{URL_PREPS}{audit_prep.id}/auto-validate/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mancante"] == 1
    assert data["findings_created"] == 1

    item.refresh_from_db()
    assert item.status == "mancante"

    finding = AuditFinding.objects.get(
        audit_prep=audit_prep, control_instance=control_instance,
    )
    assert finding.finding_type == "minor_nc"
    assert finding.auto_generated is True
    assert "mancante" in finding.title.lower()


@pytest.mark.django_db
def test_auto_validate_is_idempotent(
    client, audit_prep, control_instance, user,
):
    """Rilanciato due volte non duplica i finding aperti."""
    from apps.audit_prep.models import AuditFinding

    _make_evidence_item(audit_prep, control_instance, user)

    r1 = client.post(f"{URL_PREPS}{audit_prep.id}/auto-validate/")
    assert r1.status_code == 200
    assert r1.json()["findings_created"] == 1

    r2 = client.post(f"{URL_PREPS}{audit_prep.id}/auto-validate/")
    assert r2.status_code == 200
    data = r2.json()
    assert data["findings_created"] == 0
    assert data["findings_skipped_existing"] == 1

    assert AuditFinding.objects.filter(
        audit_prep=audit_prep, control_instance=control_instance,
    ).count() == 1


@pytest.mark.django_db
def test_auto_validate_skips_finding_when_open_major_already_exists(
    client, audit_prep, control_instance, user,
):
    """Major NC manuale gia' aperto -> nessun minor auto-generato sopra."""
    from apps.audit_prep.models import AuditFinding

    _make_evidence_item(audit_prep, control_instance, user)

    AuditFinding.objects.create(
        audit_prep=audit_prep,
        control_instance=control_instance,
        finding_type="major_nc",
        title="Major manuale",
        description="rilevato dal lead auditor",
        audit_date=date.today(),
        status="open",
        auto_generated=False,
        created_by=user,
    )

    resp = client.post(f"{URL_PREPS}{audit_prep.id}/auto-validate/")
    assert resp.status_code == 200
    data = resp.json()
    # control e' in stato "mancante" (perche' open major) ma non si crea
    # un nuovo minor_nc sopra il major esistente.
    assert data["mancante"] == 1
    assert data["findings_created"] == 0
    assert data["findings_skipped_existing"] == 1

    # Resta il solo finding manuale.
    findings = AuditFinding.objects.filter(
        audit_prep=audit_prep, control_instance=control_instance,
    )
    assert findings.count() == 1
    assert findings.first().finding_type == "major_nc"


@pytest.mark.django_db
def test_auto_validate_blocked_on_archived_prep(client, audit_prep, user):
    """Prep archiviato: l'azione viene rifiutata."""
    audit_prep.status = "archiviato"
    audit_prep.save(update_fields=["status"])

    resp = client.post(f"{URL_PREPS}{audit_prep.id}/auto-validate/")
    assert resp.status_code == 400
    assert "archiviato" in resp.json()["error"].lower()

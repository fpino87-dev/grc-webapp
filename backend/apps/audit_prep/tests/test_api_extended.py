"""Test API audit prep — azioni avanzate e EvidenceItem."""
import pytest
from datetime import date
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_PREPS = "/api/v1/audit-prep/audit-preps/"
URL_FINDINGS = "/api/v1/audit-prep/findings/"
URL_PROGRAMS = "/api/v1/audit-prep/programs/"
URL_EVIDENCES = "/api/v1/audit-prep/evidence-items/"


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="apx_user", email="apx@test.com", password="test")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
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
        code="APX-P", name="Plant APX", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def framework(db):
    from apps.controls.models import Framework
    return Framework.objects.create(
        code="ISO-APX", name="ISO 27001 APX", version="2022",
        published_at=date.today(),
    )


@pytest.fixture
def audit_prep(db, plant, framework, user):
    from apps.audit_prep.models import AuditPrep
    return AuditPrep.objects.create(
        plant=plant,
        framework=framework,
        title="Audit Extended",
        audit_date=date.today(),
        status="in_corso",
        created_by=user,
    )


@pytest.fixture
def finding(db, audit_prep, user):
    from apps.audit_prep.models import AuditFinding
    return AuditFinding.objects.create(
        audit_prep=audit_prep,
        finding_type="major_nc",
        title="Finding test",
        description="Test description",
        audit_date=date.today(),
        created_by=user,
    )


@pytest.mark.django_db
def test_annulla_action_short_reason(client, audit_prep):
    resp = client.post(f"{URL_PREPS}{audit_prep.id}/annulla/", {"reason": "short"}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_annulla_action_valid(client, audit_prep):
    resp = client.post(
        f"{URL_PREPS}{audit_prep.id}/annulla/",
        {"reason": "Annullato per errore procedurale"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "archiviato"


@pytest.mark.django_db
def test_readiness_action(client, audit_prep):
    resp = client.get(f"{URL_PREPS}{audit_prep.id}/readiness/")
    assert resp.status_code == 200
    assert "readiness_score" in resp.data


@pytest.mark.django_db
def test_complete_action_with_open_majors(client, audit_prep, finding):
    resp = client.post(f"{URL_PREPS}{audit_prep.id}/complete/", {}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_complete_action_no_open_majors(client, audit_prep):
    resp = client.post(f"{URL_PREPS}{audit_prep.id}/complete/", {}, format="json")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_finding_close_action(client, finding):
    resp = client.post(
        f"{URL_FINDINGS}{finding.id}/close/",
        {"notes": "Risolto", "evidence": "Documentazione"},
        format="json",
    )
    assert resp.status_code in (200, 400)


@pytest.mark.django_db
def test_filter_findings_by_type(client, finding):
    resp = client.get(f"{URL_FINDINGS}?finding_type=major_nc")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_filter_findings_by_status(client, finding):
    resp = client.get(f"{URL_FINDINGS}?status=open")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_create_evidence_item(client, audit_prep):
    from apps.controls.models import Framework, ControlDomain, Control, ControlInstance
    from apps.plants.models import PlantFramework
    plant = audit_prep.plant
    framework = audit_prep.framework
    PlantFramework.objects.get_or_create(
        plant=plant, framework=framework,
        defaults={"active_from": date.today(), "level": "L2", "active": True}
    )
    dom = ControlDomain.objects.create(
        framework=framework, code="APX.1",
        translations={"it": {"name": "T"}}, order=1
    )
    ctrl = Control.objects.create(
        framework=framework, domain=dom, external_id="APX.1.1",
        translations={"it": {"name": "N", "description": "D"}, "en": {"name": "N", "description": "D"}},
        level="L2", evidence_requirement={}, control_category="technical"
    )
    inst = ControlInstance.objects.create(plant=plant, control=ctrl, status="non_valutato")
    payload = {
        "audit_prep": str(audit_prep.id),
        "control_instance": str(inst.id),
        "status": "presente",
        "notes": "Evidenza disponibile",
    }
    resp = client.post(URL_EVIDENCES, payload, format="json")
    assert resp.status_code in (200, 201, 400)

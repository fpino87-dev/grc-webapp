"""Test API audit preparation."""
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
    """Utente con scope org (vede tutte le audit prep)."""
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="ap_user", email="ap@test.com", password="test")
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
        code="AP-P", name="Plant AP", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def framework(db):
    from apps.controls.models import Framework
    from datetime import date
    return Framework.objects.create(
        code="ISO-AP", name="ISO 27001 AP", version="2022",
        published_at=date.today(),
    )


@pytest.fixture
def audit_prep(db, plant, framework, user):
    from apps.audit_prep.models import AuditPrep
    return AuditPrep.objects.create(
        plant=plant,
        framework=framework,
        title="Audit ISO 27001 Q1",
        audit_date=date.today(),
        status="in_corso",
        created_by=user,
    )


@pytest.fixture
def audit_program(db, plant, framework, user):
    from apps.audit_prep.models import AuditProgram
    return AuditProgram.objects.create(
        plant=plant,
        framework=framework,
        year=2026,
        title="Programma Audit 2026",
        status="bozza",
        created_by=user,
    )


# ── AuditPrep CRUD ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_audit_preps_authenticated(client):
    resp = client.get(URL_PREPS)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_list_audit_preps_unauthenticated():
    resp = APIClient().get(URL_PREPS)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_create_audit_prep(client, plant, framework):
    payload = {
        "plant": str(plant.id),
        "framework": str(framework.id),
        "title": "Nuovo Audit TISAX",
        "audit_date": str(date.today()),
        "status": "in_corso",
    }
    resp = client.post(URL_PREPS, payload, format="json")
    assert resp.status_code == 201
    assert resp.data["title"] == "Nuovo Audit TISAX"


@pytest.mark.django_db
def test_retrieve_audit_prep(client, audit_prep):
    resp = client.get(f"{URL_PREPS}{audit_prep.id}/")
    assert resp.status_code == 200
    assert resp.data["title"] == "Audit ISO 27001 Q1"


@pytest.mark.django_db
def test_update_audit_prep(client, audit_prep):
    resp = client.patch(
        f"{URL_PREPS}{audit_prep.id}/", {"auditor_name": "Mario Rossi"}, format="json"
    )
    assert resp.status_code == 200
    assert resp.data["auditor_name"] == "Mario Rossi"


@pytest.mark.django_db
def test_delete_audit_prep(client, audit_prep):
    resp = client.delete(f"{URL_PREPS}{audit_prep.id}/")
    assert resp.status_code == 204


@pytest.mark.django_db
def test_filter_preps_by_plant(client, plant, audit_prep):
    resp = client.get(f"{URL_PREPS}?plant={plant.id}")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_audit_prep_report_action(client, audit_prep):
    resp = client.get(f"{URL_PREPS}{audit_prep.id}/report/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_audit_prep_complete_action(client, audit_prep):
    resp = client.post(f"{URL_PREPS}{audit_prep.id}/complete/", {}, format="json")
    assert resp.status_code in (200, 400)


# ── Findings ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_findings(client):
    resp = client.get(URL_FINDINGS)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_create_finding(client, audit_prep):
    payload = {
        "audit_prep": str(audit_prep.id),
        "finding_type": "major_nc",
        "title": "Mancata cifratura dati",
        "description": "Dati in chiaro su disco",
        "audit_date": str(date.today()),
    }
    resp = client.post(URL_FINDINGS, payload, format="json")
    assert resp.status_code == 201


@pytest.mark.django_db
def test_filter_findings_by_audit_prep(client, audit_prep):
    resp = client.get(f"{URL_FINDINGS}?audit_prep={audit_prep.id}")
    assert resp.status_code == 200


# ── Programs ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_programs(client):
    resp = client.get(URL_PROGRAMS)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_create_program(client, plant, framework):
    payload = {
        "plant": str(plant.id),
        "framework": str(framework.id),
        "year": 2027,
        "title": "Programma 2027",
        "status": "bozza",
    }
    resp = client.post(URL_PROGRAMS, payload, format="json")
    assert resp.status_code == 201
    assert resp.data["year"] == 2027


@pytest.mark.django_db
def test_retrieve_program(client, audit_program):
    resp = client.get(f"{URL_PROGRAMS}{audit_program.id}/")
    assert resp.status_code == 200
    assert resp.data["title"] == "Programma Audit 2026"


@pytest.mark.django_db
def test_update_program(client, audit_program):
    resp = client.patch(f"{URL_PROGRAMS}{audit_program.id}/", {"status": "approvato"}, format="json")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_delete_program(client, audit_program):
    resp = client.delete(f"{URL_PROGRAMS}{audit_program.id}/")
    assert resp.status_code == 204


@pytest.mark.django_db
def test_filter_programs_by_plant(client, plant, audit_program):
    resp = client.get(f"{URL_PROGRAMS}?plant={plant.id}")
    assert resp.status_code == 200


# ── Evidence items ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_evidence_items(client):
    resp = client.get(URL_EVIDENCES)
    assert resp.status_code == 200

"""Avanzamento DO → CHECK con caricamento diretto del file dell'evidenza."""
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

User = get_user_model()

URL_CYCLES = "/api/v1/pdca/cycles/"


@pytest.fixture(autouse=True)
def _media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="pdca_up", email="pdca_up@test.com", password="x")
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
    return Plant.objects.create(code="UP-P", name="Plant UP", country="IT", nis2_scope="non_soggetto", status="attivo")


def _cycle_in_do(plant):
    from apps.pdca.services import create_cycle
    c = create_cycle(plant=plant, title="Ciclo upload", trigger_type="manual")
    c.fase_corrente = "do"
    c.save(update_fields=["fase_corrente"])
    return c


def _pdf(name="verbale.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4 verbale di implementazione", content_type="application/pdf")


@pytest.mark.django_db
def test_upload_new_evidence_advances_to_check(client, plant):
    from apps.documents.models import Evidence
    cycle = _cycle_in_do(plant)
    resp = client.post(f"{URL_CYCLES}{cycle.id}/advance/",
                       {"notes": "Fatto", "file": _pdf(), "evidence_title": "Verbale formazione"},
                       format="multipart")
    assert resp.status_code == 200, resp.data
    assert resp.data["fase_corrente"] == "check"
    ev = Evidence.objects.get(pk=resp.data["evidence_id"])
    assert ev.title == "Verbale formazione"
    assert ev.plant_id == plant.id
    assert ev.valid_until is None
    assert ev.file_path
    phase = cycle.phases.get(phase="do")
    assert phase.evidence_id == ev.id


@pytest.mark.django_db
def test_upload_default_title_and_org_cycle_evidence_has_no_site(client):
    from apps.documents.models import Evidence
    cycle = _cycle_in_do(None)
    resp = client.post(f"{URL_CYCLES}{cycle.id}/advance/", {"file": _pdf()}, format="multipart")
    assert resp.status_code == 200, resp.data
    ev = Evidence.objects.get(pk=resp.data["evidence_id"])
    assert ev.title == "PDCA — Ciclo upload"
    assert ev.plant_id is None


@pytest.mark.django_db
def test_file_and_existing_evidence_together_rejected(client, plant, user):
    from apps.documents.models import Evidence
    cycle = _cycle_in_do(plant)
    ev = Evidence.objects.create(title="Esistente", plant=plant, created_by=user)
    resp = client.post(f"{URL_CYCLES}{cycle.id}/advance/",
                       {"file": _pdf(), "evidence_id": str(ev.id)}, format="multipart")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_file_outside_do_rejected(client, plant):
    from apps.pdca.services import create_cycle
    cycle = create_cycle(plant=plant, title="In plan", trigger_type="manual")
    resp = client.post(f"{URL_CYCLES}{cycle.id}/advance/",
                       {"notes": "x" * 30, "file": _pdf()}, format="multipart")
    assert resp.status_code == 400
    cycle.refresh_from_db()
    assert cycle.fase_corrente == "plan"


@pytest.mark.django_db
def test_invalid_file_rejected_without_side_effects(client, plant):
    from apps.documents.models import Evidence
    cycle = _cycle_in_do(plant)
    bad = SimpleUploadedFile("script.exe", b"MZ\x90\x00binary", content_type="application/octet-stream")
    resp = client.post(f"{URL_CYCLES}{cycle.id}/advance/", {"file": bad}, format="multipart")
    assert resp.status_code == 400
    assert resp.data["error"]
    cycle.refresh_from_db()
    assert cycle.fase_corrente == "do"
    assert not Evidence.objects.exists()

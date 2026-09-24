"""Audit di seconda/terza parte: tipo, committente, rapporto ufficiale allegato,
PDCA dei finding con il tipo di audit, snapshot M13 e pacchetto audit."""
import io
import zipfile

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

User = get_user_model()

URL_PREPS = "/api/v1/audit-prep/audit-preps/"
URL_FINDINGS = "/api/v1/audit-prep/findings/"


@pytest.fixture(autouse=True)
def _media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="ext_co", email="ext_co@test.com", password="x")
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
    return Plant.objects.create(code="EXT-P", name="Plant EXT", country="IT", nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def prep(client, plant):
    resp = client.post(URL_PREPS, {
        "plant": str(plant.id), "title": "Audit cliente OEM 2026", "audit_date": "2026-09-10",
        "audit_type": "seconda_parte", "requesting_party": "OEM Alfa", "auditor_name": "Ente Beta",
    }, format="json")
    assert resp.status_code == 201, resp.data
    return resp.data


def _pdf():
    return SimpleUploadedFile("rapporto.pdf", b"%PDF-1.4 rapporto di audit", content_type="application/pdf")


@pytest.mark.django_db
def test_create_second_party_audit(prep):
    assert prep["audit_type"] == "seconda_parte"
    assert prep["requesting_party"] == "OEM Alfa"
    assert prep["report_evidence"] is None


@pytest.mark.django_db
def test_audit_type_filter(client, plant, prep):
    client.post(URL_PREPS, {"plant": str(plant.id), "title": "Interno"}, format="json")
    rows = client.get(URL_PREPS, {"audit_type": "seconda_parte"}).data["results"]
    assert [r["title"] for r in rows] == ["Audit cliente OEM 2026"]


@pytest.mark.django_db
def test_attach_replace_and_detach_official_report(client, plant, prep):
    from apps.documents.models import Evidence
    url = f"{URL_PREPS}{prep['id']}/report-file/"
    resp = client.post(url, {"file": _pdf()}, format="multipart")
    assert resp.status_code == 201, resp.data
    first = Evidence.objects.get(pk=resp.data["report_evidence"])
    assert first.evidence_type == "report"
    assert first.plant_id == plant.id
    assert first.valid_until is None
    assert resp.data["report_evidence_title"] == "Rapporto audit — Audit cliente OEM 2026"

    resp = client.post(url, {"file": _pdf(), "title": "Rapporto rev.1"}, format="multipart")
    assert resp.status_code == 201
    assert resp.data["report_evidence_title"] == "Rapporto rev.1"
    assert Evidence.objects.filter(pk=first.pk).exists()  # il precedente resta archiviato

    assert client.delete(url).status_code == 204
    assert client.get(f"{URL_PREPS}{prep['id']}/").data["report_evidence"] is None
    assert Evidence.objects.count() == 2


@pytest.mark.django_db
def test_report_requires_valid_file(client, prep):
    url = f"{URL_PREPS}{prep['id']}/report-file/"
    assert client.post(url, {}, format="multipart").status_code == 400
    bad = SimpleUploadedFile("x.exe", b"MZ\x90\x00", content_type="application/octet-stream")
    assert client.post(url, {"file": bad}, format="multipart").status_code == 400


@pytest.mark.django_db
def test_report_evidence_not_settable_via_patch(client, user, prep):
    from apps.documents.models import Evidence
    ev = Evidence.objects.create(title="Qualsiasi", created_by=user)
    client.patch(f"{URL_PREPS}{prep['id']}/", {"report_evidence": str(ev.id)}, format="json")
    assert client.get(f"{URL_PREPS}{prep['id']}/").data["report_evidence"] is None


@pytest.mark.django_db
def test_external_auditor_cannot_attach_report(prep):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="ext_aud", email="ext_aud@test.com", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.EXTERNAL_AUDITOR, scope_type="org")
    c = APIClient()
    c.force_authenticate(user=u)
    assert c.post(f"{URL_PREPS}{prep['id']}/report-file/", {"file": _pdf()}, format="multipart").status_code == 403


@pytest.mark.django_db
def test_finding_pdca_inherits_audit_type_and_auditor(client, prep):
    from apps.audit_prep.models import AuditFinding
    resp = client.post(URL_FINDINGS, {
        "audit_prep": prep["id"], "finding_type": "minor_nc", "title": "Log non conservati",
        "description": "Retention insufficiente", "audit_date": "2026-09-10",
    }, format="json")
    assert resp.status_code == 201, resp.data
    finding = AuditFinding.objects.get(pk=resp.data["id"])
    assert finding.auditor_name == "Ente Beta"
    assert finding.pdca_cycle.audit_subtype == "seconda_parte"


@pytest.mark.django_db
def test_snapshot_lists_audit_type_and_party(prep, plant):
    from apps.management_review.services.snapshot import _audit_block
    import datetime
    today = timezone.localdate()
    block = _audit_block({"plant_id": plant.id}, today, timezone.now() - datetime.timedelta(days=365))
    row = next(a for a in block["elenco_audit"] if a["id"] == prep["id"])
    assert row["audit_type"] == "seconda_parte"
    assert row["requesting_party"] == "OEM Alfa"


@pytest.mark.django_db
def test_audit_package_includes_external_reports(client, plant, prep):
    from django.core.files.storage import default_storage
    from apps.controls.views.audit_package import _add_external_audit_reports
    client.post(f"{URL_PREPS}{prep['id']}/report-file/", {"file": _pdf()}, format="multipart")
    client.post(URL_PREPS, {"plant": str(plant.id), "title": "Audit interno Q3"}, format="json")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        _add_external_audit_reports(zf, "PKG", plant.id, default_storage)
    with zipfile.ZipFile(buf) as zf:
        names = zf.namelist()
        index = zf.read("PKG/AUDIT_ESTERNI/RIEPILOGO.csv").decode("utf-8-sig")
    assert any(n.startswith("PKG/AUDIT_ESTERNI/2026-09-10_") and n.endswith(".pdf") for n in names)
    assert "OEM Alfa" in index and "Ente Beta" in index
    assert "Audit interno Q3" not in index


# ── Seconda parte: nessuna checklist ────────────────────────────────────────

@pytest.fixture
def tisax_l3(db, plant):
    from apps.controls.models import Framework
    from apps.plants.models import PlantFramework
    fw = Framework.objects.create(code="TISAX_L3", name="TISAX AL3", version="6.0", published_at=timezone.localdate())
    PlantFramework.objects.create(plant=plant, framework=fw, active_from=timezone.localdate())
    return fw


@pytest.mark.django_db
def test_second_party_never_seeds_checklist(client, plant, tisax_l3):
    from apps.audit_prep.models import AuditPrep
    resp = client.post(URL_PREPS, {"plant": str(plant.id), "title": "Audit OEM su VDA ISA",
                                   "framework": str(tisax_l3.id), "audit_type": "seconda_parte"}, format="json")
    assert resp.status_code == 201
    prep = AuditPrep.objects.get(pk=resp.data["id"])
    assert prep.evidence_items.count() == 0
    assert prep.uses_checklist is False


@pytest.mark.django_db
def test_second_party_rejects_checklist_actions(client, prep):
    url = f"{URL_PREPS}{prep['id']}/"
    assert client.post(f"{url}sync-controls/").status_code == 400
    resp = client.post(f"{url}auto-validate/")
    assert resp.status_code == 400 and "seconda parte" in resp.data["error"]
    assert client.get(f"{url}readiness/").data["readiness_score"] is None


@pytest.mark.django_db
def test_second_party_report_html_has_no_readiness(client, prep):
    resp = client.get(f"{URL_PREPS}{prep['id']}/report/")
    html = resp.content.decode()
    assert "Readiness Score" not in html and "Controlli verificati" not in html
    assert "Finding rilevati" in html


@pytest.mark.django_db
def test_second_party_snapshot_without_readiness(prep, plant):
    import datetime
    from apps.audit_prep.models import AuditPrep
    from apps.management_review.services.snapshot import _audit_block
    AuditPrep.objects.filter(pk=prep["id"]).update(readiness_score=80)
    block = _audit_block({"plant_id": plant.id}, timezone.localdate(), timezone.now() - datetime.timedelta(days=365))
    row = next(a for a in block["elenco_audit"] if a["id"] == prep["id"])
    assert row["readiness_score"] is None

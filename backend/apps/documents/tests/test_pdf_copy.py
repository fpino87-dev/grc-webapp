"""Copia PDF dei documenti Word e file consegnati all'auditor (M07).

- al caricamento di un .docx la versione è "da generare" e il PDF viene creato
  dal servizio di conversione (qui simulato);
- restano in storage i file dell'ultima versione e di quella in vigore;
- il pacchetto audit consegna la versione in vigore, in PDF quando c'è.
"""
import datetime
import io
import zipfile
from unittest.mock import MagicMock, patch

import pytest
import requests
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
User = get_user_model()

FAKE_PDF = b"%PDF-1.7 copia generata"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@pytest.fixture(autouse=True)
def _media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    settings.GOTENBERG_URL = "http://gotenberg:3000"


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="pdf_co", email="pdf_co@test.com", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def approver(db):
    return User.objects.create_user(username="pdf_appr", email="pdf_appr@test.com", password="x")


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="PDF-P", name="Plant PDF", country="IT",
                                nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def document(plant, user):
    from apps.documents.models import Document
    return Document.objects.create(
        title="Politica sicurezza", category="politica", document_type="politica",
        status="bozza", plant=plant, created_by=user, document_code="POL-01",
    )


def _docx(text="Politica"):
    import docx

    d = docx.Document()
    d.add_paragraph(text)
    buf = io.BytesIO()
    d.save(buf)
    return SimpleUploadedFile("Politica.docx", buf.getvalue(), content_type=DOCX_MIME)


def _gotenberg_ok():
    resp = MagicMock(status_code=200, content=FAKE_PDF)
    return patch("apps.documents.pdf_converter.requests.post", return_value=resp)


def _upload(document, user, file, captured):
    from apps.documents.services import add_version_with_file
    with captured(execute=True):
        return add_version_with_file(document, file, user)


def _approve(document, approver, captured):
    from apps.documents.services import approve_document
    document.status = "revisione"
    document.save(update_fields=["status"])
    with captured(execute=True):
        approve_document(document, approver)
    document.refresh_from_db()


# ── Conversione ────────────────────────────────────────────────────────────

def test_word_upload_generates_pdf_copy(document, user, django_capture_on_commit_callbacks):
    from core.audit import AuditLog

    with _gotenberg_ok() as post:
        version = _upload(document, user, _docx(), django_capture_on_commit_callbacks)
    version.refresh_from_db()
    assert post.call_args.args[0] == "http://gotenberg:3000/forms/libreoffice/convert"
    assert version.pdf_status == "ok"
    assert version.pdf_storage_path.endswith("/pdf/Politica.pdf")
    with default_storage.open(version.pdf_storage_path, "rb") as fh:
        assert fh.read() == FAKE_PDF
    assert version.storage_path.endswith("Politica.docx")  # l'originale resta
    assert AuditLog.objects.filter(action_code="document.pdf_generated").exists()


def test_pdf_upload_needs_no_copy(document, user, django_capture_on_commit_callbacks):
    pdf = SimpleUploadedFile("policy.pdf", b"%PDF-1.4 contenuto", content_type="application/pdf")
    with _gotenberg_ok() as post:
        version = _upload(document, user, pdf, django_capture_on_commit_callbacks)
    version.refresh_from_db()
    assert version.pdf_status == "na"
    post.assert_not_called()


def test_service_down_leaves_version_pending(document, user, django_capture_on_commit_callbacks):
    with patch("apps.documents.pdf_converter.requests.post",
               side_effect=requests.ConnectionError("down")):
        version = _upload(document, user, _docx(), django_capture_on_commit_callbacks)
    version.refresh_from_db()
    assert version.pdf_status == "pending"

    from apps.documents.services import generate_pending_pdfs
    with _gotenberg_ok():
        counts = generate_pending_pdfs()
    version.refresh_from_db()
    assert counts["ok"] == 1
    assert version.pdf_status == "ok"


def test_rejected_file_is_failed_and_not_retried_nightly(document, user, django_capture_on_commit_callbacks):
    from apps.documents.services import generate_pending_pdfs

    bad = MagicMock(status_code=400, content=b"bad request")
    with patch("apps.documents.pdf_converter.requests.post", return_value=bad):
        version = _upload(document, user, _docx(), django_capture_on_commit_callbacks)
    version.refresh_from_db()
    assert version.pdf_status == "failed"

    with _gotenberg_ok() as post:
        generate_pending_pdfs()
    post.assert_not_called()
    with _gotenberg_ok():
        generate_pending_pdfs(include_failed=True)
    version.refresh_from_db()
    assert version.pdf_status == "ok"


def test_conversion_disabled_keeps_pending(settings, document, user, django_capture_on_commit_callbacks):
    settings.GOTENBERG_URL = ""
    with _gotenberg_ok() as post:
        version = _upload(document, user, _docx(), django_capture_on_commit_callbacks)
    version.refresh_from_db()
    assert version.pdf_status == "pending"
    post.assert_not_called()


def test_pdf_fields_not_writable_via_api(client, document, user, django_capture_on_commit_callbacks):
    with _gotenberg_ok():
        version = _upload(document, user, _docx(), django_capture_on_commit_callbacks)
    client.patch(f"/api/v1/documents/document-versions/{version.id}/",
                 {"pdf_status": "failed", "pdf_storage_path": "../../etc/passwd"}, format="json")
    version.refresh_from_db()
    assert version.pdf_status == "ok"
    assert "etc/passwd" not in version.pdf_storage_path


# ── File conservati ────────────────────────────────────────────────────────

def test_approved_version_files_survive_new_drafts(document, user, approver,
                                                   django_capture_on_commit_callbacks):
    with _gotenberg_ok():
        v1 = _upload(document, user, _docx("uno"), django_capture_on_commit_callbacks)
        _approve(document, approver, django_capture_on_commit_callbacks)
        v2 = _upload(document, user, _docx("due"), django_capture_on_commit_callbacks)
        v3 = _upload(document, user, _docx("tre"), django_capture_on_commit_callbacks)
    for v in (v1, v2, v3):
        v.refresh_from_db()

    # v1 è in vigore: originale e PDF restano anche con due bozze successive
    assert default_storage.exists(v1.storage_path)
    assert default_storage.exists(v1.pdf_storage_path)
    # v2 non è né l'ultima né quella in vigore: file rimossi, resta la riga
    assert v2.storage_path == "" and v2.pdf_storage_path == ""
    assert v2.sha256
    assert default_storage.exists(v3.storage_path)

    # approvata v3, anche v1 è superata
    _approve(document, approver, django_capture_on_commit_callbacks)
    v1.refresh_from_db()
    assert v1.storage_path == "" and v1.pdf_storage_path == ""
    v3.refresh_from_db()
    assert default_storage.exists(v3.pdf_storage_path)


# ── File consegnato all'esterno ────────────────────────────────────────────

def test_export_file_prefers_approved_version_pdf(document, user, approver,
                                                  django_capture_on_commit_callbacks):
    from apps.documents.services import export_file

    with _gotenberg_ok():
        v1 = _upload(document, user, _docx("uno"), django_capture_on_commit_callbacks)
        _approve(document, approver, django_capture_on_commit_callbacks)
        _upload(document, user, _docx("bozza"), django_capture_on_commit_callbacks)
    v1.refresh_from_db()

    exported = export_file(document)
    assert exported["version"].pk == v1.pk
    assert exported["is_pdf_copy"] is True
    assert exported["is_approved_version"] is True
    assert exported["extension"] == ".pdf"
    assert exported["sha256"] == v1.pdf_sha256


def test_export_file_falls_back_to_original_word(document, user, django_capture_on_commit_callbacks):
    from apps.documents.services import export_file

    with patch("apps.documents.pdf_converter.requests.post",
               side_effect=requests.ConnectionError("down")):
        version = _upload(document, user, _docx(), django_capture_on_commit_callbacks)
    exported = export_file(document)
    assert exported["version"].pk == version.pk
    assert exported["is_pdf_copy"] is False
    assert exported["pdf_missing"] is True
    assert exported["extension"] == ".docx"
    assert exported["is_approved_version"] is False


def test_audit_package_ships_pdf_of_approved_version(client, plant, document, user, approver,
                                                    django_capture_on_commit_callbacks):
    from apps.controls.models import Control, ControlInstance, Framework

    fw = Framework.objects.create(code="ISO27001", name="ISO", version="1",
                                  published_at=datetime.date(2024, 1, 1))
    ctrl = Control.objects.create(framework=fw, external_id="A.5.1",
                                  translations={"title": {"it": "Politiche"}})
    ci = ControlInstance.objects.create(plant=plant, control=ctrl, status="compliant")
    ci.documents.add(document)

    with _gotenberg_ok():
        _upload(document, user, _docx("in vigore"), django_capture_on_commit_callbacks)
        _approve(document, approver, django_capture_on_commit_callbacks)
        _upload(document, user, _docx("bozza"), django_capture_on_commit_callbacks)

    resp = client.get("/api/v1/controls/audit-package/",
                      {"framework": "ISO27001", "plant": str(plant.id)})
    assert resp.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(b"".join(resp.streaming_content)
                                    if hasattr(resp, "streaming_content") else resp.content))
    names = zf.namelist()
    doc_files = [n for n in names if "/documenti/" in n]
    assert len(doc_files) == 1
    assert doc_files[0].endswith("POL-01_Politica_sicurezza.pdf")
    assert zf.read(doc_files[0]) == FAKE_PDF
    index = [n for n in names if n.endswith("/DOCUMENTI.csv")]
    assert index
    rows = zf.read(index[0]).decode("utf-8-sig")
    assert "PDF (copia del file Word)" in rows
    assert "v1" in rows


# ── Download ───────────────────────────────────────────────────────────────

def test_download_pdf_endpoint(client, document, user, django_capture_on_commit_callbacks):
    url = f"/api/v1/documents/documents/{document.id}/download-pdf/"
    with patch("apps.documents.pdf_converter.requests.post",
               side_effect=requests.ConnectionError("down")):
        _upload(document, user, _docx(), django_capture_on_commit_callbacks)
    assert client.get(url).status_code == 404

    from apps.documents.services import generate_pending_pdfs
    with _gotenberg_ok():
        generate_pending_pdfs()
    resp = client.get(url)
    assert resp.status_code == 200
    assert b"".join(resp.streaming_content) == FAKE_PDF
    assert 'filename="Politica.pdf"' in resp["Content-Disposition"]


def test_convert_command_reports_disabled(settings, capsys):
    from django.core.management import call_command

    settings.GOTENBERG_URL = ""
    call_command("convert_document_pdfs")
    assert "GOTENBERG_URL" in capsys.readouterr().err

"""Test limiti upload e body size (newfix S12) + cross-check ext/MIME (#11)."""
import pytest
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from core.uploads import EVIDENCE_EXTENSIONS, EVIDENCE_MIME_TYPES, validate_uploaded_file

import base64
import io
import zipfile

PDF_BYTES = b"%PDF-1.4\n%fake pdf body\n1 0 obj\n<<>>\nendobj\n"


def _docx_bytes_marker_past_header():
    """Costruisce un .docx valido in cui il marker `word/` finisce oltre i
    primi 2048 byte (entry [Content_Types].xml grande e non compressa), come
    accade nei documenti reali di Word. Con la sola lettura di 2048 byte
    libmagic ripiegava su application/octet-stream → falso rifiuto."""
    buf = io.BytesIO()
    z = zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED)
    z.writestr(
        "[Content_Types].xml",
        '<?xml version="1.0"?><Types>' + ("A" * 6000) + "</Types>",
    )
    z.writestr("word/document.xml", "<x/>")
    z.close()
    return buf.getvalue()
# PNG 1x1 reale: un header sintetico con IHDR azzerato non viene riconosciuto
# da libmagic (application/octet-stream).
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


def test_data_upload_max_memory_size_set():
    """JSON body cap ~5 MB per impedire denial-of-memory."""
    assert settings.DATA_UPLOAD_MAX_MEMORY_SIZE == 5 * 1024 * 1024


def test_file_upload_max_memory_size_set():
    """File >50 MB vengono streamati su disco invece di stare in RAM."""
    assert settings.FILE_UPLOAD_MAX_MEMORY_SIZE == 50 * 1024 * 1024


def test_data_upload_max_number_fields_set():
    """Cap esplicito sul numero di campi POST per richiesta."""
    assert settings.DATA_UPLOAD_MAX_NUMBER_FIELDS == 1000


# ── Cross-check estensione ↔ MIME (newfix 2026-06-09 #11) ────────────────────

def _file(name, content):
    return SimpleUploadedFile(name, content, content_type="application/octet-stream")


def test_pdf_content_with_pdf_extension_ok():
    validate_uploaded_file(_file("report.pdf", PDF_BYTES))


def test_pdf_content_with_docx_extension_rejected():
    """Prima del fix passava: entrambi i MIME erano in whitelist."""
    with pytest.raises(ValidationError, match="docx"):
        validate_uploaded_file(_file("report.docx", PDF_BYTES))


def test_png_content_with_jpg_extension_rejected():
    with pytest.raises(ValidationError, match="jpg"):
        validate_uploaded_file(_file("foto.jpg", PNG_BYTES))


def test_png_content_with_png_extension_ok():
    validate_uploaded_file(_file("foto.png", PNG_BYTES))


def test_docx_with_markers_past_2048_bytes_ok():
    """Regressione: un .docx reale con i marker OOXML oltre i primi 2048 byte
    non deve essere rifiutato. Prima del fix libmagic vedeva solo la testa e
    restituiva application/octet-stream → 400 sull'upload di nuova versione."""
    validate_uploaded_file(_file("verbale.docx", _docx_bytes_marker_past_header()))


def test_csv_detected_as_text_plain_ok():
    """libmagic spesso classifica i CSV come text/plain: non va rifiutato."""
    validate_uploaded_file(
        _file("dati.csv", b"col1,col2\n1,2\n3,4\n"),
        allowed_extensions=EVIDENCE_EXTENSIONS,
        allowed_mimes=EVIDENCE_MIME_TYPES,
    )

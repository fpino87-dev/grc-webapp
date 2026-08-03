"""Test limiti upload e body size (newfix S12) + cross-check ext/MIME (#11)."""
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

import core.uploads as uploads
from core.uploads import EVIDENCE_EXTENSIONS, EVIDENCE_MIME_TYPES, validate_uploaded_file

import base64
import io
import zipfile

PDF_BYTES = b"%PDF-1.4\n%fake pdf body\n1 0 obj\n<<>>\nendobj\n"


def _ooxml_bytes(*, first_entry, part, extra=()):
    """Costruisce un pacchetto OPC (OOXML) minimale, controllando quale entry
    viene scritto per primo. Word/Excel scrivono `[Content_Types].xml` per
    primo, ma altri strumenti mettono `_rels/.rels` o la parte principale: in
    quel caso libmagic non riconosce lo specifico MIME Office."""
    buf = io.BytesIO()
    z = zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED)
    entries = {
        "_rels/.rels": "<Relationships/>",
        "[Content_Types].xml": '<?xml version="1.0"?><Types/>',
        part: "<x/>",
    }
    entries.update(extra)
    # scrivi prima `first_entry`, poi il resto nell'ordine di inserimento
    z.writestr(first_entry, entries.pop(first_entry))
    for name, data in entries.items():
        z.writestr(name, data)
    z.close()
    return buf.getvalue()


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


def test_docx_with_rels_as_first_entry_ok():
    """Regressione (file reale utente): un .docx valido in cui il PRIMO entry
    dello ZIP è `_rels/.rels` (non `[Content_Types].xml`). A seconda della
    versione della magic DB, libmagic può non riconoscere lo specifico MIME
    Office e restituire application/octet-stream → 400. Il fallback OPC via
    zipfile lo accetta comunque (contiene [Content_Types].xml + word/)."""
    validate_uploaded_file(
        _file("manuale.docx", _ooxml_bytes(first_entry="_rels/.rels", part="word/document.xml"))
    )


# I test seguenti forzano libmagic a restituire application/octet-stream (la
# condizione osservata sul file reale dell'utente), così il ramo di fallback
# OPC è esercitato in modo deterministico, indipendente dalla magic DB locale.

def test_ooxml_fallback_accepts_valid_docx_when_libmagic_says_octet_stream():
    data = _ooxml_bytes(first_entry="_rels/.rels", part="word/document.xml")
    with patch.object(uploads.magic, "from_buffer", return_value="application/octet-stream"):
        validate_uploaded_file(_file("manuale.docx", data))


def test_ooxml_fallback_rejects_xlsx_renamed_to_docx():
    """Un vero .xlsx rinominato .docx: ha la cartella `xl/`, non `word/` → il
    fallback OPC non lo accetta (cross-check estensione preservato)."""
    data = _ooxml_bytes(first_entry="_rels/.rels", part="xl/workbook.xml")
    with patch.object(uploads.magic, "from_buffer", return_value="application/octet-stream"):
        with pytest.raises(ValidationError):
            validate_uploaded_file(_file("finto.docx", data))


def test_ooxml_fallback_rejects_plain_zip_renamed_to_docx():
    """Uno ZIP generico (senza [Content_Types].xml) rinominato .docx non deve
    passare il fallback OPC."""
    buf = io.BytesIO()
    z = zipfile.ZipFile(buf, "w")
    z.writestr("foo/bar.txt", "hi")
    z.close()
    with patch.object(uploads.magic, "from_buffer", return_value="application/octet-stream"):
        with pytest.raises(ValidationError):
            validate_uploaded_file(_file("finto.docx", buf.getvalue()))


def test_ooxml_fallback_rejects_non_zip_renamed_to_docx():
    """Un PDF rinominato .docx: non è uno ZIP → BadZipFile → rifiutato anche
    se libmagic dà octet-stream."""
    with patch.object(uploads.magic, "from_buffer", return_value="application/octet-stream"):
        with pytest.raises(ValidationError):
            validate_uploaded_file(_file("finto.docx", PDF_BYTES))


def test_ooxml_fallback_accepts_valid_xlsx_when_libmagic_says_zip():
    data = _ooxml_bytes(first_entry="_rels/.rels", part="xl/workbook.xml")
    with patch.object(uploads.magic, "from_buffer", return_value="application/zip"):
        validate_uploaded_file(
            _file("dati.xlsx", data),
            allowed_extensions=EVIDENCE_EXTENSIONS,
            allowed_mimes=EVIDENCE_MIME_TYPES,
        )


def test_csv_detected_as_text_plain_ok():
    """libmagic spesso classifica i CSV come text/plain: non va rifiutato."""
    validate_uploaded_file(
        _file("dati.csv", b"col1,col2\n1,2\n3,4\n"),
        allowed_extensions=EVIDENCE_EXTENSIONS,
        allowed_mimes=EVIDENCE_MIME_TYPES,
    )

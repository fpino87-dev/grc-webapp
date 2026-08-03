"""
Validatori upload file riutilizzabili (CLAUDE.md regola #12).

Esegue tre check obbligatori su qualunque file caricato dagli utenti:
1. Dimensione massima
2. Estensione in whitelist
3. MIME type reale via python-magic (anti extension spoofing)

I preset coprono i casi tipici: documenti d'ufficio, evidenze (PDF + immagini),
allegati incidente. Per casi nuovi, comporre `validate_uploaded_file(file, allowed_extensions=..., allowed_mimes=..., max_bytes=...)`.
"""

import io
import os
import zipfile

import magic
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


DEFAULT_MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

# Documenti d'ufficio (M07 Documents)
OFFICE_EXTENSIONS = {
    "doc", "docx", "xls", "xlsx", "ppt", "pptx", "pdf", "png", "jpg", "jpeg",
}
OFFICE_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "image/png",
    "image/jpeg",
}

# Evidenze (audit_prep, BCP test, controlli): documenti + screenshot
EVIDENCE_EXTENSIONS = OFFICE_EXTENSIONS | {"txt", "csv"}
EVIDENCE_MIME_TYPES = OFFICE_MIME_TYPES | {"text/plain", "text/csv", "application/csv"}

# Cross-check estensione ↔ MIME reale (newfix 2026-06-09 #11): senza questa
# mappa un file .docx con contenuto PDF passava la validazione perché entrambi
# i MIME erano in whitelist. I legacy Office (doc/xls/ppt) condividono il
# container OLE2, quindi libmagic può riportare il MIME di un altro membro
# della famiglia: per quelli si accetta l'intera famiglia legacy.
_LEGACY_OFFICE_MIMES = {
    "application/msword",
    "application/vnd.ms-excel",
    "application/vnd.ms-powerpoint",
}
EXT_TO_MIME: dict[str, set[str]] = {
    "pdf":  {"application/pdf"},
    "doc":  _LEGACY_OFFICE_MIMES,
    "xls":  _LEGACY_OFFICE_MIMES,
    "ppt":  _LEGACY_OFFICE_MIMES,
    "docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    "xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    "pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation"},
    "png":  {"image/png"},
    "jpg":  {"image/jpeg"},
    "jpeg": {"image/jpeg"},
    "txt":  {"text/plain"},
    # I CSV vengono spesso rilevati come text/plain da libmagic
    "csv":  {"text/csv", "application/csv", "text/plain"},
}

# Gli OOXML sono contenitori ZIP (OPC). libmagic li classifica con lo specifico
# MIME Office SOLO se `[Content_Types].xml` è il PRIMO entry dell'archivio
# (convenzione, non requisito, di MS Word/Excel). File prodotti o ri-zippati da
# altri strumenti mettono `_rels/.rels` o `word/document.xml` per primo: allora
# libmagic ripiega su application/zip o application/octet-stream e un file
# perfettamente valido verrebbe rifiutato. Per questi casi validiamo la
# struttura OPC direttamente via zipfile (entry `[Content_Types].xml` + cartella
# di parte attesa), che è indipendente dall'ordine degli entry.
_OOXML_EXT_MARKERS = {
    "docx": "word/",
    "xlsx": "xl/",
    "pptx": "ppt/",
}
_ZIP_LIKE_MIMES = {"application/zip", "application/octet-stream"}


def _looks_like_ooxml(content: bytes, part_prefix: str) -> bool:
    """True se ``content`` è un pacchetto OPC (OOXML) con la parte attesa.

    Ispeziona solo la central directory (namelist), non estrae nulla: sicuro
    anche su archivi ostili. Un non-ZIP (es. PDF rinominato .docx) solleva
    BadZipFile → False; un altro OOXML rinominato (xlsx→.docx) non ha la
    cartella attesa → False (cross-check estensione preservato)."""
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            names = zf.namelist()
    except zipfile.BadZipFile:
        return False
    if "[Content_Types].xml" not in names:
        return False
    return any(name.startswith(part_prefix) for name in names)


def validate_uploaded_file(
    uploaded_file,
    *,
    allowed_extensions=None,
    allowed_mimes=None,
    max_bytes=None,
):
    """
    Valida un file caricato. Solleva ValidationError se non rispetta i vincoli.
    Default: documenti d'ufficio + 50MB.
    """
    allowed_extensions = allowed_extensions or OFFICE_EXTENSIONS
    allowed_mimes = allowed_mimes or OFFICE_MIME_TYPES
    max_bytes = max_bytes or DEFAULT_MAX_FILE_SIZE_BYTES

    if uploaded_file.size > max_bytes:
        mb = max_bytes // (1024 * 1024)
        raise ValidationError(_("File troppo grande. Dimensione massima: %(mb)sMB.") % {"mb": mb})

    # NB: non spacchettare in `_, ext`: `_` e' gettext a livello modulo e il
    # local shadowing causava UnboundLocalError sul ramo "file troppo grande".
    ext = os.path.splitext(getattr(uploaded_file, "name", "") or "")[1]
    ext = ext.lstrip(".").lower()
    if not ext or ext not in allowed_extensions:
        raise ValidationError(
            _("Estensione file non consentita. Formati ammessi: %(formats)s.")
            % {"formats": ", ".join(sorted(allowed_extensions))}
        )

    # NB: leggere l'intero contenuto, non solo i primi 2048 byte. Il size cap
    # sopra garantisce che qui il file sia ≤ max_bytes, e il contenuto serve
    # comunque interamente per l'eventuale ispezione OPC (vedi sotto).
    uploaded_file.seek(0)
    content = uploaded_file.read()
    uploaded_file.seek(0)
    mime_type = magic.from_buffer(content, mime=True)

    # Fallback OOXML: se l'estensione è docx/xlsx/pptx ma libmagic ha restituito
    # un MIME ZIP-generico (perché `[Content_Types].xml` non è il primo entry),
    # verifichiamo la struttura OPC via zipfile e, se valida, normalizziamo il
    # MIME a quello atteso per l'estensione. Vedi _looks_like_ooxml.
    part_prefix = _OOXML_EXT_MARKERS.get(ext)
    if (
        part_prefix is not None
        and mime_type in _ZIP_LIKE_MIMES
        and _looks_like_ooxml(content, part_prefix)
    ):
        mime_type = next(iter(EXT_TO_MIME[ext]))

    if mime_type not in allowed_mimes:
        raise ValidationError(
            _("Tipo di file non consentito. Il contenuto del file non corrisponde all'estensione.")
        )

    # newfix #11 — il MIME deve corrispondere proprio a QUELLA estensione,
    # non genericamente alla whitelist. Estensioni fuori mappa ricadono sul
    # solo check di whitelist fatto sopra.
    expected = EXT_TO_MIME.get(ext)
    if expected is not None and mime_type not in expected:
        raise ValidationError(
            _("Il contenuto del file non corrisponde all'estensione .%(ext)s.")
            % {"ext": ext}
        )

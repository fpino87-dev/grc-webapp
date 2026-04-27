"""
Validatori upload file riutilizzabili (CLAUDE.md regola #12).

Esegue tre check obbligatori su qualunque file caricato dagli utenti:
1. Dimensione massima
2. Estensione in whitelist
3. MIME type reale via python-magic (anti extension spoofing)

I preset coprono i casi tipici: documenti d'ufficio, evidenze (PDF + immagini),
allegati incidente. Per casi nuovi, comporre `validate_uploaded_file(file, allowed_extensions=..., allowed_mimes=..., max_bytes=...)`.
"""

import os

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

    _, ext = os.path.splitext(getattr(uploaded_file, "name", "") or "")
    ext = ext.lstrip(".").lower()
    if not ext or ext not in allowed_extensions:
        raise ValidationError(
            _("Estensione file non consentita. Formati ammessi: %(formats)s.")
            % {"formats": ", ".join(sorted(allowed_extensions))}
        )

    uploaded_file.seek(0)
    header = uploaded_file.read(2048)
    uploaded_file.seek(0)
    mime_type = magic.from_buffer(header, mime=True)
    if mime_type not in allowed_mimes:
        raise ValidationError(
            _("Tipo di file non consentito. Il contenuto del file non corrisponde all'estensione.")
        )

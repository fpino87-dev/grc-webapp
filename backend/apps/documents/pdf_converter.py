"""Client del servizio di conversione PDF (Gotenberg, route LibreOffice).

Solo trasporto HTTP: la decisione su quali versioni convertire, dove salvare il
PDF e come registrarlo sta in ``services.py``. Il servizio gira nella rete
interna di compose e non raggiunge internet (vedi docker-compose*.yml).
"""

import requests
from django.conf import settings

# Formati di testo modificabili che vengono accompagnati da una copia PDF.
# Fogli di calcolo e presentazioni restano nel formato originale.
CONVERTIBLE_EXTENSIONS = {"doc", "docx"}


class ConversionUnavailable(Exception):
    """Servizio non raggiungibile o sovraccarico: si riprova più tardi."""


class ConversionFailed(Exception):
    """Il servizio ha rifiutato il file: riprovare non cambia l'esito."""


def is_enabled() -> bool:
    return bool(getattr(settings, "GOTENBERG_URL", ""))


def is_convertible(file_name: str) -> bool:
    ext = (file_name or "").lower().rsplit(".", 1)
    return len(ext) == 2 and ext[1] in CONVERTIBLE_EXTENSIONS


def convert_to_pdf(file_name: str, content: bytes) -> bytes:
    """Converte un documento Word in PDF e ne restituisce i byte."""
    if not is_enabled():
        raise ConversionUnavailable("conversione PDF non configurata (GOTENBERG_URL)")
    url = settings.GOTENBERG_URL.rstrip("/") + "/forms/libreoffice/convert"
    try:
        response = requests.post(
            url,
            files={"files": (file_name, content)},
            timeout=settings.GOTENBERG_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise ConversionUnavailable(str(exc)) from exc

    # 503/504/429: servizio occupato o conversione andata in timeout lato
    # Gotenberg; gli altri errori dicono che il file non è convertibile.
    if response.status_code in (429, 502, 503, 504):
        raise ConversionUnavailable(f"HTTP {response.status_code}")
    if response.status_code != 200:
        raise ConversionFailed(f"HTTP {response.status_code}")
    if not response.content.startswith(b"%PDF"):
        raise ConversionFailed("risposta non PDF")
    return response.content

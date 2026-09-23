"""Risposte d'errore senza dettagli interni.

Il testo di un'eccezione imprevista (SQL, percorsi, messaggi di librerie) non va
mai rimandato al client: il dettaglio, con traceback, resta nel log del server
e all'utente arriva un messaggio generico.
"""
import logging

from django.utils.translation import gettext as _
from rest_framework.response import Response

logger = logging.getLogger("grc.errors")


def internal_error_response(context: str, status: int = 500) -> Response:
    """Da chiamare dentro un blocco `except`: registra l'eccezione in corso
    (con traceback) e restituisce un errore generico."""
    logger.exception("Errore imprevisto: %s", context)
    return Response(
        {"error": _("Operazione non riuscita per un errore interno. Il dettaglio è nel log del server.")},
        status=status,
    )

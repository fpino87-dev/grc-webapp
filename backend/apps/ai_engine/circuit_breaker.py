"""
Circuit breaker per i provider LLM (M20).

Evita di martellare un provider già giù: dopo `FAILURE_THRESHOLD` fallimenti
consecutivi entro la finestra, il circuito si "apre" per `COOLDOWN_SECONDS` e
`route()` salta quel provider (fail-fast → fallback immediato) invece di
aspettare il timeout HTTP a ogni richiesta. Un successo richiude il circuito.

Stato persistito in cache (Redis condiviso tra worker). Se la cache non è
disponibile il breaker degrada a "sempre chiuso" (no-op): non deve mai essere
lui a impedire una chiamata AI.
"""
from __future__ import annotations

import logging
import time

from django.core.cache import cache

logger = logging.getLogger(__name__)

FAILURE_THRESHOLD = 3       # fallimenti consecutivi prima di aprire
COOLDOWN_SECONDS = 120      # quanto resta aperto prima di ritentare
_FAILS_TTL = 300            # i contatori di fallimento scadono da soli

_PREFIX = "ai_cb"


def _fails_key(name: str) -> str:
    return f"{_PREFIX}:{name}:fails"


def _open_key(name: str) -> str:
    return f"{_PREFIX}:{name}:open_until"


def is_open(name: str) -> bool:
    """True se il circuito per `name` è aperto (provider da saltare)."""
    try:
        open_until = cache.get(_open_key(name))
    except Exception as exc:  # cache giù → non blocchiamo le chiamate
        logger.warning("circuit breaker: cache non disponibile (is_open): %s", exc)
        return False
    return bool(open_until) and time.time() < open_until


def record_failure(name: str) -> None:
    """Registra un fallimento; al raggiungimento della soglia apre il circuito."""
    try:
        try:
            fails = cache.incr(_fails_key(name))
        except ValueError:
            # chiave inesistente → inizializza
            cache.set(_fails_key(name), 1, _FAILS_TTL)
            fails = 1
        if fails >= FAILURE_THRESHOLD:
            cache.set(_open_key(name), time.time() + COOLDOWN_SECONDS, COOLDOWN_SECONDS)
            cache.delete(_fails_key(name))
            logger.warning(
                "circuit breaker: provider '%s' APERTO per %ss dopo %s fallimenti",
                name, COOLDOWN_SECONDS, fails,
            )
    except Exception as exc:
        logger.warning("circuit breaker: cache non disponibile (record_failure): %s", exc)


def record_success(name: str) -> None:
    """Un successo richiude il circuito e azzera i contatori."""
    try:
        cache.delete(_fails_key(name))
        cache.delete(_open_key(name))
    except Exception as exc:
        logger.warning("circuit breaker: cache non disponibile (record_success): %s", exc)


def reset(name: str) -> None:
    """Reset esplicito (usato dai test / da un'azione manuale)."""
    record_success(name)

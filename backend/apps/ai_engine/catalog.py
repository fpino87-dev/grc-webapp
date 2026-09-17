"""Catalogo dei modelli realmente disponibili presso i provider.

Il catalogo statico `MODELS_BY_PROVIDER` è stato la causa di un guasto reale:
elencava modelli Groq (`llama-3.1-8b-instant`, `llama-3.3-70b-versatile`,
`mixtral-8x7b-32768`) che il provider ha nel frattempo dismesso. L'interfaccia
li offriva ancora, l'utente ne sceglieva uno, e ogni chiamata falliva con un
errore opaco — «Nessun provider AI disponibile» — che non diceva la cosa
importante: *quel modello non esiste più*.

I cataloghi dei provider cambiano ogni pochi mesi; una lista scritta nel codice
è garantita diventare falsa. Qui la si chiede al provider, con una cache breve
per non interrogarlo a ogni apertura della pagina, e il catalogo statico resta
solo come ripiego quando la rete o la chiave non ci sono.
"""
import logging
import time

from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_TTL = 15 * 60
CACHE_PREFIX = "ai_models"

# Modelli che un provider elenca ma che non sanno generare testo: audio,
# embedding, classificatori di sicurezza. Offrirli in un menù a tendina di
# «modello per le sintesi» significa solo far scegliere qualcosa che poi
# fallisce.
NON_TEXT_HINTS = (
    "whisper", "tts", "embed", "rerank", "moderation", "guard", "orpheus",
    "stable-diffusion", "dall-e", "image", "vision-encoder",
)

# Preferenze per la scelta automatica quando il modello configurato non esiste
# più: sottostringhe in ordine di gradimento. Non sono nomi esatti proprio
# perché i nomi cambiano — si cerca la famiglia, non la versione.
PREFERRED = {
    "anthropic": ("claude-sonnet", "claude-haiku", "claude"),
    "openai":    ("gpt-4o-mini", "gpt-4o", "gpt-4", "gpt"),
    "groq":      ("llama-3.3", "llama-3.1", "llama-3", "gpt-oss-120b", "qwen", "gpt-oss", "compound"),
    "google":    ("gemini-2.0-flash", "gemini-1.5-flash", "flash", "gemini"),
    "mistral":   ("mistral-small", "mistral-medium", "mistral-large", "mistral"),
}


def is_text_model(model_id: str) -> bool:
    lowered = (model_id or "").lower()
    return not any(hint in lowered for hint in NON_TEXT_HINTS)


def _cache_key(kind: str, config) -> str:
    if kind == "local":
        return f"{CACHE_PREFIX}:local:{config.local_endpoint}"
    return f"{CACHE_PREFIX}:cloud:{config.cloud_provider}:{config.pk}"


def fetch_cloud_models(config, refresh: bool = False) -> dict:
    """Modelli di testo offerti dal provider cloud configurato.

    Ritorna `{"models": [...], "error": str|None, "fetched_at": float}`;
    non solleva: un provider irraggiungibile è un'informazione da mostrare,
    non un errore che deve rompere la pagina delle impostazioni.
    """
    key = _cache_key("cloud", config)
    if not refresh:
        cached = cache.get(key)
        if cached:
            return cached

    result = {"models": [], "error": None, "fetched_at": time.time()}
    if not config.api_key:
        result["error"] = "no_api_key"
        return result

    try:
        if config.cloud_provider == "anthropic":
            import anthropic

            client = anthropic.Anthropic(api_key=config.api_key)
            ids = [m.id for m in client.models.list(limit=100).data]
        else:
            import httpx

            from .router import BASE_URLS

            base = BASE_URLS.get(config.cloud_provider)
            if not base:
                result["error"] = "unsupported_provider"
                return result
            resp = httpx.get(
                f"{base}/models",
                headers={"Authorization": f"Bearer {config.api_key}"},
                timeout=15,
            )
            resp.raise_for_status()
            ids = [m["id"] for m in resp.json().get("data", []) if m.get("id")]
        result["models"] = sorted(i for i in ids if is_text_model(i))
    except Exception as exc:  # rete, chiave revocata, provider in errore
        # Mai loggare la chiave: `exc` dei client HTTP non la contiene, ma si
        # tronca comunque il messaggio (regola #11).
        logger.warning("Elenco modelli non disponibile per %s: %s", config.cloud_provider, str(exc)[:200])
        result["error"] = str(exc)[:200]

    cache.set(key, result, CACHE_TTL)
    return result


def fetch_local_models(config, refresh: bool = False) -> dict:
    """Modelli scaricati sull'istanza Ollama configurata."""
    key = _cache_key("local", config)
    if not refresh:
        cached = cache.get(key)
        if cached:
            return cached

    result = {"models": [], "error": None, "fetched_at": time.time()}
    try:
        import httpx

        resp = httpx.get(f"{config.local_endpoint}/api/tags", timeout=10)
        resp.raise_for_status()
        result["models"] = sorted(
            m["name"] for m in resp.json().get("models", []) if m.get("name")
        )
    except Exception as exc:
        logger.warning("Elenco modelli locali non disponibile: %s", str(exc)[:200])
        result["error"] = str(exc)[:200]

    cache.set(key, result, CACHE_TTL)
    return result


def available_models(config, refresh: bool = False) -> dict:
    """Quadro completo per la pagina delle impostazioni.

    Dice anche — ed è il punto — se il modello **attualmente configurato**
    esiste ancora presso il provider.
    """
    cloud = fetch_cloud_models(config, refresh=refresh)
    local = fetch_local_models(config, refresh=refresh)
    return {
        "cloud": {
            "provider": config.cloud_provider,
            "configured": config.cloud_model,
            # None = non verificabile (nessuna chiave, provider irraggiungibile):
            # diverso da False, che significa "verificato e non c'è più".
            "configured_available": (
                config.cloud_model in cloud["models"] if cloud["models"] else None
            ),
            **cloud,
        },
        "local": {
            "endpoint": config.local_endpoint,
            "configured": config.local_model,
            "configured_available": (
                config.local_model in local["models"] if local["models"] else None
            ),
            **local,
        },
    }


def resolve_cloud_model(config) -> tuple[str, str | None]:
    """Modello cloud da usare per una chiamata: `(model, sostituito_da)`.

    Se quello configurato è ancora offerto dal provider si usa quello, senza
    discussioni. Se è sparito si sceglie il migliore disponibile secondo
    `PREFERRED` invece di far fallire la richiesta: un riesame di direzione non
    deve restare senza bozza perché il provider ha dismesso un modello. La
    sostituzione non viene però mai nascosta — finisce nei log, nel risultato
    della chiamata e nei metadati di ciò che l'IA produce.

    Non si riscrive la configurazione: quale modello usare stabilmente è una
    decisione di chi governa il sistema, non un effetto collaterale.
    """
    catalog = fetch_cloud_models(config)
    models = catalog.get("models") or []
    if not models or config.cloud_model in models:
        # Nessun elenco (chiave assente, provider giù) → si prova comunque con
        # quello configurato: meglio un tentativo che un rifiuto a priori.
        return config.cloud_model, None

    for hint in PREFERRED.get(config.cloud_provider, ()):
        for model in models:
            if hint in model.lower():
                return model, config.cloud_model
    return models[0], config.cloud_model

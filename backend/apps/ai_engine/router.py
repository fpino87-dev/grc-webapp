"""
AiRouter — routing local/cloud con fallback.
"""

import hashlib
import logging
import uuid

from django.utils import timezone

from . import circuit_breaker

logger = logging.getLogger(__name__)


class LlmUnavailable(Exception):
    """Sollevata quando nessun provider LLM è raggiungibile (cloud + fallback
    locale entrambi giù). Permette ai chiamanti di degradare con grazia
    (es. HTTP 503) invece di propagare un errore opaco."""


def _call_ollama(prompt: str, model: str, endpoint: str, system: str = "", timeout: int = 60) -> str:
    import httpx

    payload = {"model": model, "prompt": prompt, "stream": False}
    if system:
        payload["system"] = system
    resp = httpx.post(f"{endpoint}/api/generate", json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json().get("response", "")


def _call_anthropic(prompt: str, model: str, api_key: str, system: str = "", max_tokens: int = 2048) -> tuple[str, int]:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    msgs = [{"role": "user", "content": prompt}]
    kwargs = {"model": model, "max_tokens": max_tokens, "messages": msgs}
    if system:
        kwargs["system"] = system
    resp = client.messages.create(**kwargs)
    tokens = resp.usage.input_tokens + resp.usage.output_tokens
    return resp.content[0].text, tokens


def _call_openai_compatible(
    prompt: str, model: str, api_key: str, base_url: str, system: str = "", max_tokens: int = 2048
) -> tuple[str, int]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = client.chat.completions.create(model=model, messages=messages, max_tokens=max_tokens)
    tokens = resp.usage.total_tokens if resp.usage else 0
    return resp.choices[0].message.content, tokens


BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "groq": "https://api.groq.com/openai/v1",
    "google": "https://generativelanguage.googleapis.com/v1beta/openai",
    "mistral": "https://api.mistral.ai/v1",
}


def route(
    task_type: str,
    prompt: str,
    system: str = "",
    user=None,
    entity_id=None,
    module_source: str = "M20",
    sanitize: bool = True,
    plant_ids: list | None = None,
    max_tokens: int = 2048,
    timeout: int = 60,
) -> dict:
    from .models import AiInteractionLog, AiProviderConfig

    config = AiProviderConfig.get_active()
    if not config:
        raise ValueError("Nessuna configurazione AI attiva. Configurare in Impostazioni -> AI Engine.")

    config.reset_budget_if_needed()

    token_map = {}
    if sanitize:
        from .sanitizer import Sanitizer

        sanitized, token_map = Sanitizer().sanitize({"text": prompt}, plant_ids or [])
        prompt_to_send = sanitized["text"]
    else:
        prompt_to_send = prompt

    task_provider = config.get_task_provider(task_type)
    used_fallback = False
    text = ""
    tokens_used = 0
    provider_used = ""
    model_used = ""

    cloud_key = f"cloud:{config.cloud_provider}"
    ollama_key = "ollama"

    if task_provider == "cloud" and config.budget_remaining <= 0:
        task_provider = "ollama"
        used_fallback = True
        if not config.fallback_notified:
            _notify_budget_exhausted(config, user)
            config.fallback_notified = True
            config.save(update_fields=["fallback_notified"])

    # Circuit breaker: se il cloud è già marcato giù, salta direttamente al
    # fallback locale (fail-fast) senza attendere il timeout HTTP a ogni richiesta.
    if task_provider == "cloud" and circuit_breaker.is_open(cloud_key):
        logger.info(
            "Cloud provider '%s' circuito aperto — fallback Ollama (fail-fast)",
            config.cloud_provider,
        )
        used_fallback = True
        task_provider = "ollama"

    if task_provider == "cloud":
        try:
            text, tokens_used = _call_cloud(config, prompt_to_send, system, max_tokens)
            provider_used = config.cloud_provider
            model_used = config.cloud_model
            config.tokens_used_month += tokens_used
            config.save(update_fields=["tokens_used_month", "updated_at"])
            circuit_breaker.record_success(cloud_key)
        except Exception as exc:
            logger.warning("Cloud AI error (%s): %s — fallback Ollama", config.cloud_provider, exc)
            circuit_breaker.record_failure(cloud_key)
            used_fallback = True
            task_provider = "ollama"

    if task_provider == "ollama":
        try:
            text = _call_ollama(prompt_to_send, config.local_model, config.local_endpoint, system, timeout)
            circuit_breaker.record_success(ollama_key)
        except Exception as exc:
            circuit_breaker.record_failure(ollama_key)
            logger.error(
                "LLM non disponibile (cloud_fallback=%s, ollama giù): %s", used_fallback, exc
            )
            raise LlmUnavailable(
                "Nessun provider AI disponibile (cloud e fallback locale non raggiungibili)."
            ) from exc
        provider_used = "ollama"
        model_used = config.local_model
        tokens_used = 0

    if sanitize and token_map:
        from .sanitizer import Sanitizer

        text = Sanitizer().desanitize(text, token_map)

    interaction_id = None
    # `entity_id` è una UUIDField: i chiamanti che lavorano su entità sintetiche
    # (es. gli insight del Centro Operativo, identificati da un fingerprint hash,
    # non da una pk) non hanno un UUID reale. In quel caso si salta la telemetria
    # invece di far esplodere la richiesta con un 500 (la chiamata AI è andata a
    # buon fine: l'output non deve andare perso per un dettaglio di logging).
    def _as_uuid(value):
        try:
            return uuid.UUID(str(value))
        except (ValueError, TypeError, AttributeError):
            return None

    if user and entity_id and _as_uuid(entity_id) is not None:
        log = AiInteractionLog.objects.create(
            user_id=user.pk,
            function=task_type,
            module_source=module_source,
            entity_id=entity_id,
            model_used=f"{provider_used}/{model_used}",
            input_hash=hashlib.sha256(prompt.encode()).hexdigest(),
            output_ai=text[:5000],
        )
        interaction_id = str(log.id)

    return {
        "text": text,
        "provider": provider_used,
        "model": model_used,
        "used_fallback": used_fallback,
        "tokens_used": tokens_used,
        "interaction_id": interaction_id,
    }


def _call_cloud(config, prompt: str, system: str, max_tokens: int = 2048) -> tuple[str, int]:
    provider = config.cloud_provider
    model = config.cloud_model
    api_key = config.api_key

    if provider == "anthropic":
        return _call_anthropic(prompt, model, api_key, system, max_tokens)
    if provider in BASE_URLS:
        return _call_openai_compatible(prompt, model, api_key, BASE_URLS[provider], system, max_tokens)
    raise ValueError(f"Provider {provider} non supportato")


def _notify_budget_exhausted(config, user):
    try:
        from apps.notifications.resolver import fire_notification

        fire_notification(
            "ai_budget_exhausted",
            context={
                "tokens_used": config.tokens_used_month,
                "monthly_budget": config.monthly_token_budget,
                "reset_day": config.budget_reset_day,
            },
        )
    except Exception as exc:
        logger.warning("Notifica budget AI fallita: %s", exc)


def confirm_output(interaction_id: str, user, final_text: str) -> None:
    from .models import AiInteractionLog

    AiInteractionLog.objects.filter(id=interaction_id).update(
        output_human_final=final_text[:5000],
        confirmed_by_id=user.pk,
        confirmed_at=timezone.now(),
    )


def ignore_output(interaction_id: str) -> None:
    from .models import AiInteractionLog

    AiInteractionLog.objects.filter(id=interaction_id).update(ignored=True)

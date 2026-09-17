"""Catalogo dei modelli vivo: elenco, ripiego e sostituzione automatica.

Il guasto che ha motivato questo modulo: il catalogo statico offriva modelli
Groq dismessi, l'utente ne sceglieva uno e ogni chiamata falliva con un errore
che non nominava la causa.
"""
import pytest
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def config(db):
    from apps.ai_engine.models import AiProviderConfig
    return AiProviderConfig.objects.create(
        name="Test", active=True, cloud_provider="groq",
        cloud_model="llama-3.3-70b-versatile", api_key="k-test",
        local_endpoint="http://ollama.test:11434", local_model="llama3.2:3b",
    )


def _models_response(ids):
    resp = MagicMock()
    resp.json.return_value = {"data": [{"id": i} for i in ids]}
    resp.raise_for_status.return_value = None
    return resp


def _tags_response(names):
    resp = MagicMock()
    resp.json.return_value = {"models": [{"name": n} for n in names]}
    resp.raise_for_status.return_value = None
    return resp


# ── Elenco ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_non_text_models_are_filtered_out(config):
    """Offrire whisper o un classificatore in un menù «modello per le sintesi»
    significa far scegliere qualcosa che poi fallisce."""
    from apps.ai_engine.catalog import fetch_cloud_models
    with patch("httpx.get", return_value=_models_response([
        "openai/gpt-oss-120b", "whisper-large-v3", "meta-llama/llama-prompt-guard-2-86m",
        "qwen/qwen3.8-27b", "text-embedding-3-small",
    ])):
        out = fetch_cloud_models(config, refresh=True)
    assert out["models"] == ["openai/gpt-oss-120b", "qwen/qwen3.8-27b"]
    assert out["error"] is None


@pytest.mark.django_db
def test_list_is_cached_between_calls(config):
    from apps.ai_engine.catalog import fetch_cloud_models
    with patch("httpx.get", return_value=_models_response(["a-model"])) as get:
        fetch_cloud_models(config, refresh=True)
        fetch_cloud_models(config)
        assert get.call_count == 1


@pytest.mark.django_db
def test_provider_error_is_reported_not_raised(config):
    """La pagina delle impostazioni deve aprirsi anche se il provider è giù."""
    from apps.ai_engine.catalog import fetch_cloud_models
    with patch("httpx.get", side_effect=RuntimeError("connessione rifiutata")):
        out = fetch_cloud_models(config, refresh=True)
    assert out["models"] == [] and "connessione rifiutata" in out["error"]


@pytest.mark.django_db
def test_no_api_key_is_not_an_error_call(config):
    from apps.ai_engine.catalog import fetch_cloud_models
    config.api_key = ""
    with patch("httpx.get") as get:
        out = fetch_cloud_models(config, refresh=True)
    assert out["error"] == "no_api_key" and not get.called


@pytest.mark.django_db
def test_available_models_flags_a_decommissioned_model(config):
    from apps.ai_engine.catalog import available_models
    with patch("httpx.get", side_effect=[
        _models_response(["openai/gpt-oss-120b"]), _tags_response(["llama3.2:3b"]),
    ]):
        out = available_models(config, refresh=True)
    assert out["cloud"]["configured_available"] is False   # verificato: non c'è più
    assert out["local"]["configured_available"] is True


@pytest.mark.django_db
def test_unverifiable_is_none_not_false(config):
    """Senza elenco non si può dire che il modello non esista: None ≠ False."""
    from apps.ai_engine.catalog import available_models
    with patch("httpx.get", side_effect=RuntimeError("rete assente")):
        out = available_models(config, refresh=True)
    assert out["cloud"]["configured_available"] is None
    assert out["local"]["configured_available"] is None


# ── Sostituzione automatica ───────────────────────────────────────────────

@pytest.mark.django_db
def test_configured_model_is_kept_when_still_offered(config):
    from apps.ai_engine.catalog import resolve_cloud_model
    with patch("httpx.get", return_value=_models_response(["llama-3.3-70b-versatile", "altro"])):
        assert resolve_cloud_model(config) == ("llama-3.3-70b-versatile", None)


@pytest.mark.django_db
def test_best_available_is_used_when_model_was_decommissioned(config):
    """Un riesame non deve restare senza bozza perché il provider ha dismesso
    un modello — ma la sostituzione viene dichiarata, non nascosta."""
    from apps.ai_engine.catalog import resolve_cloud_model
    with patch("httpx.get", return_value=_models_response([
        "allam-2-7b", "qwen/qwen3.8-27b", "openai/gpt-oss-120b",
    ])):
        model, substituted = resolve_cloud_model(config)
    assert model == "openai/gpt-oss-120b"          # preferenza per il più capace
    assert substituted == "llama-3.3-70b-versatile"


@pytest.mark.django_db
def test_without_a_list_the_configured_model_is_tried_anyway(config):
    from apps.ai_engine.catalog import resolve_cloud_model
    with patch("httpx.get", side_effect=RuntimeError("rete assente")):
        assert resolve_cloud_model(config) == ("llama-3.3-70b-versatile", None)


# ── Router ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_router_declares_the_substitution(config):
    from apps.ai_engine import router
    with patch("httpx.get", return_value=_models_response(["openai/gpt-oss-120b"])), \
         patch.object(router, "_call_cloud", return_value=("testo", 10)) as call:
        out = router.route("chatbot", "prompt", sanitize=False)
    assert out["model_substituted"] == "llama-3.3-70b-versatile"
    assert out["model"] == "openai/gpt-oss-120b"
    assert call.call_args.kwargs["model"] == "openai/gpt-oss-120b"


@pytest.mark.django_db
def test_local_fallback_gets_its_own_timeout(config):
    """L'inferenza locale su CPU si misura in minuti: il timeout del cloud la
    interrompeva a metà generazione facendola sembrare irraggiungibile."""
    from apps.ai_engine import router
    config.task_routing = {"chatbot": "ollama"}
    config.save(update_fields=["task_routing"])
    with patch.object(router, "_call_ollama", return_value="testo") as call:
        router.route("chatbot", "prompt", sanitize=False, timeout=30, max_tokens=800)
    assert call.call_args[0][4] >= router.LOCAL_MIN_TIMEOUT
    # e il limite di lunghezza chiesto dal chiamante arriva anche a Ollama
    assert call.call_args.kwargs["max_tokens"] == 800


@pytest.mark.django_db
def test_error_message_names_both_failures(config):
    from apps.ai_engine import router
    with patch("httpx.get", return_value=_models_response(["openai/gpt-oss-120b"])), \
         patch.object(router, "_call_cloud", side_effect=RuntimeError("model_not_found")), \
         patch.object(router, "_call_ollama", side_effect=RuntimeError("timed out")):
        with pytest.raises(router.LlmUnavailable) as exc:
            router.route("chatbot", "prompt", sanitize=False)
    message = str(exc.value)
    assert "model_not_found" in message and "llama3.2:3b" in message and "timed out" in message


# ── API ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_endpoint_returns_live_lists(config):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="ai_admin", email="aiadmin@test.com",
                                 password="x", is_superuser=True)
    UserPlantAccess.objects.create(user=u, role=GrcRole.SUPER_ADMIN, scope_type="org")
    c = APIClient()
    c.force_authenticate(user=u)
    with patch("httpx.get", side_effect=[
        _models_response(["openai/gpt-oss-120b", "whisper-large-v3"]),
        _tags_response(["llama3.2:3b", "mistral-nemo:latest"]),
    ]):
        resp = c.get(f"/api/v1/ai/config/{config.id}/available-models/?refresh=1")
    assert resp.status_code == 200
    assert resp.data["cloud"]["models"] == ["openai/gpt-oss-120b"]
    assert resp.data["local"]["models"] == ["llama3.2:3b", "mistral-nemo:latest"]


@pytest.mark.django_db
def test_endpoint_is_admin_only(config):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="ai_pm", email="aipm@test.com", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.PLANT_MANAGER, scope_type="org")
    c = APIClient()
    c.force_authenticate(user=u)
    assert c.get(f"/api/v1/ai/config/{config.id}/available-models/").status_code == 403

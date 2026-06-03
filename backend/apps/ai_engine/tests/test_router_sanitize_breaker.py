"""P1-4 — AI Engine: garanzie su (1) nessun PII inviato al cloud senza sanitize,
(2) circuit breaker + fallback quando l'LLM è giù.

I provider sono mockati: nessuna chiamata di rete reale, nessun costo cloud.
"""
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.ai_engine import circuit_breaker
from apps.ai_engine.router import LlmUnavailable, route

User = get_user_model()

# PII di prova (tutti fittizi)
PII_EMAIL = "mario.rossi@acme.example"
PII_IP = "10.20.30.40"
PII_CF = "RSSMRA80A01H501U"
PII_PHONE = "3331234567"
PII_PIVA = "12345678903"


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="AICONF", name="Stabilimento Riservato", country="IT",
        nis2_scope="essenziale", status="attivo",
    )


@pytest.fixture
def ai_config(db):
    """Config AI attiva che instrada il task di test sul cloud."""
    from apps.ai_engine.models import AiProviderConfig
    return AiProviderConfig.objects.create(
        name="test-config",
        active=True,
        cloud_provider="anthropic",
        cloud_model="claude-haiku-4-5-20251001",
        api_key="sk-test-fittizia",
        monthly_token_budget=100000,
        tokens_used_month=0,
        task_routing={"unit_test": "cloud"},
    )


@pytest.fixture(autouse=True)
def _reset_breaker():
    """Azzera il circuito (cache Redis condivisa) prima e dopo ogni test."""
    for key in ("cloud:anthropic", "ollama"):
        circuit_breaker.reset(key)
    yield
    for key in ("cloud:anthropic", "ollama"):
        circuit_breaker.reset(key)


# ───────────────────────────────────────────────────────────────────────────
# 1. No-PII-leak
# ───────────────────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_no_pii_reaches_cloud_provider(ai_config, plant):
    """Il prompt che arriva al provider cloud non deve contenere PII in chiaro;
    la risposta col token del plant viene ripristinata (desanitize)."""
    raw = (
        f"Contatta {PII_EMAIL} al {PII_PHONE}, server {PII_IP}, "
        f"CF {PII_CF}, P.IVA {PII_PIVA}, presso {plant.name}."
    )

    captured = {}

    def fake_cloud(config, prompt, system, max_tokens):
        captured["prompt"] = prompt
        return "[PLANT_A] presenta un gap di conformità.", 42

    with patch("apps.ai_engine.router._call_cloud", side_effect=fake_cloud):
        result = route(task_type="unit_test", prompt=raw, plant_ids=[plant.pk])

    sent = captured["prompt"]
    # Nessun PII in chiaro nel prompt inviato
    for pii in (PII_EMAIL, PII_IP, PII_CF, PII_PHONE, PII_PIVA, plant.name):
        assert pii not in sent, f"PII trapelata al provider: {pii!r}"
    # I placeholder ci sono
    assert "[EMAIL_REMOVED]" in sent
    assert "[IP_REMOVED]" in sent
    assert "[CF_REMOVED]" in sent
    assert "[PLANT_A]" in sent
    # La risposta è stata de-sanitizzata (token plant → nome reale)
    assert plant.name in result["text"]
    assert "[PLANT_A]" not in result["text"]


@pytest.mark.django_db
def test_sanitize_is_on_by_default(ai_config, plant):
    """route() sanitizza di default (sanitize=True) anche senza passare il flag."""
    captured = {}

    def fake_cloud(config, prompt, system, max_tokens):
        captured["prompt"] = prompt
        return "ok", 1

    with patch("apps.ai_engine.router._call_cloud", side_effect=fake_cloud):
        route(task_type="unit_test", prompt=f"email {PII_EMAIL}")

    assert PII_EMAIL not in captured["prompt"]


@pytest.mark.django_db
def test_sanitizer_unit_replaces_all_pii_classes(plant):
    """Test diretto del Sanitizer su tutte le classi di PII + desanitize plant."""
    from apps.ai_engine.sanitizer import Sanitizer

    raw = f"{PII_EMAIL} {PII_IP} {PII_CF} {PII_PHONE} presso {plant.name}."
    out, token_map = Sanitizer().sanitize({"text": raw}, [plant.pk])
    text = out["text"]
    assert PII_EMAIL not in text and PII_IP not in text and PII_CF not in text
    assert plant.name not in text
    # desanitize ripristina il valore reale del plant
    restored = Sanitizer().desanitize(text, token_map)
    assert plant.name in restored


# ───────────────────────────────────────────────────────────────────────────
# 2. Fallback + circuit breaker
# ───────────────────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_cloud_failure_falls_back_to_ollama(ai_config):
    with patch("apps.ai_engine.router._call_cloud", side_effect=RuntimeError("cloud 500")), \
         patch("apps.ai_engine.router._call_ollama", return_value="risposta locale") as ollama:
        result = route(task_type="unit_test", prompt="ciao", sanitize=False)

    assert result["used_fallback"] is True
    assert result["provider"] == "ollama"
    assert result["text"] == "risposta locale"
    ollama.assert_called_once()


@pytest.mark.django_db
def test_both_providers_down_raises_llm_unavailable(ai_config):
    with patch("apps.ai_engine.router._call_cloud", side_effect=RuntimeError("cloud giù")), \
         patch("apps.ai_engine.router._call_ollama", side_effect=RuntimeError("ollama giù")):
        with pytest.raises(LlmUnavailable):
            route(task_type="unit_test", prompt="ciao", sanitize=False)


@pytest.mark.django_db
def test_circuit_opens_and_skips_cloud_after_threshold(ai_config):
    """Dopo FAILURE_THRESHOLD fallimenti cloud, il circuito si apre e le chiamate
    successive saltano il cloud (fail-fast) usando direttamente il fallback."""
    threshold = circuit_breaker.FAILURE_THRESHOLD

    cloud = patch("apps.ai_engine.router._call_cloud", side_effect=RuntimeError("cloud giù"))
    ollama = patch("apps.ai_engine.router._call_ollama", return_value="locale")
    with cloud as cloud_mock, ollama:
        # threshold chiamate: ognuna prova il cloud e fallisce → fallback ollama
        for _ in range(threshold):
            route(task_type="unit_test", prompt="x", sanitize=False)
        assert cloud_mock.call_count == threshold
        assert circuit_breaker.is_open("cloud:anthropic") is True

        # chiamata successiva: cloud NON viene più chiamato (fail-fast)
        result = route(task_type="unit_test", prompt="x", sanitize=False)
        assert cloud_mock.call_count == threshold  # invariato
        assert result["used_fallback"] is True
        assert result["provider"] == "ollama"


@pytest.mark.django_db
def test_cloud_success_resets_circuit(ai_config):
    circuit_breaker.record_failure("cloud:anthropic")
    circuit_breaker.record_failure("cloud:anthropic")
    with patch("apps.ai_engine.router._call_cloud", return_value=("ok", 5)):
        route(task_type="unit_test", prompt="x", sanitize=False)
    # un successo azzera i contatori → nessun residuo che porti all'apertura
    assert circuit_breaker.is_open("cloud:anthropic") is False


# ───────────────────────────────────────────────────────────────────────────
# 3. Degradazione HTTP controllata (503)
# ───────────────────────────────────────────────────────────────────────────
@pytest.fixture
def co_user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="ai_co", email="ai_co@test.com", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.mark.django_db
def test_explain_returns_503_when_llm_unavailable(co_user, plant, ai_config):
    client = APIClient()
    client.force_authenticate(user=co_user)
    gap = {"kind": "risk_expired", "title": "X", "subtitle": "Y", "details": {}}

    with patch("apps.ai_engine.router.route", side_effect=LlmUnavailable("giù")):
        res = client.post(
            "/api/v1/ai/assistant/explain/",
            {"plant_id": str(plant.id), "gap": gap},
            format="json",
        )
    assert res.status_code == 503
    assert "non disponibile" in res.data["error"].lower()

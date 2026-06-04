"""Test — salute degli enricher a chiave (semaforo impostazioni OSINT).

Tutte le chiamate di rete sono mockate.
"""
import pytest
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.osint import health
from apps.osint.health import classify_http, check_enricher_health, KEYED_PROVIDERS
from apps.osint.enrichers import virustotal, abusech, gsb
from apps.osint.models import OsintSettings

User = get_user_model()
pytestmark = pytest.mark.django_db


class _Resp:
    def __init__(self, code):
        self.status_code = code


# ---------------------------------------------------------------------------
# classify_http
# ---------------------------------------------------------------------------

class TestClassifyHttp:
    def test_ok_2xx_and_404(self):
        assert classify_http(200) == "ok"
        assert classify_http(204) == "ok"
        assert classify_http(404) == "ok"  # autenticato, risorsa neutra assente

    def test_invalid(self):
        assert classify_http(401) == "invalid"
        assert classify_http(403) == "invalid"

    def test_rate_limited(self):
        assert classify_http(429) == "rate_limited"

    def test_error(self):
        assert classify_http(500) == "error"
        assert classify_http(400) == "error"  # default: 400 non è invalid

    def test_gsb_400_is_invalid(self):
        # GSB segnala la chiave non valida con 400
        assert classify_http(400, invalid_codes=(400, 401, 403)) == "invalid"


# ---------------------------------------------------------------------------
# probe per-enricher
# ---------------------------------------------------------------------------

class TestProbes:
    def test_no_key_returns_no_key(self):
        s = OsintSettings.load()
        s.virustotal_api_key = ""
        s.abusech_api_key = ""
        assert virustotal.probe(s) == ("no_key", "")
        assert abusech.probe(s) == ("no_key", "")

    def test_virustotal_ok(self):
        s = OsintSettings.load()
        s.virustotal_api_key = "k"
        with patch.object(virustotal.requests, "get", return_value=_Resp(200)):
            status, detail = virustotal.probe(s)
        assert status == "ok"
        assert "200" in detail

    def test_virustotal_invalid(self):
        s = OsintSettings.load()
        s.virustotal_api_key = "bad"
        with patch.object(virustotal.requests, "get", return_value=_Resp(401)):
            assert virustotal.probe(s)[0] == "invalid"

    def test_virustotal_rate_limited(self):
        s = OsintSettings.load()
        s.virustotal_api_key = "k"
        with patch.object(virustotal.requests, "get", return_value=_Resp(429)):
            assert virustotal.probe(s)[0] == "rate_limited"

    def test_virustotal_network_error(self):
        s = OsintSettings.load()
        s.virustotal_api_key = "k"
        with patch.object(virustotal.requests, "get", side_effect=Exception("boom")):
            status, detail = virustotal.probe(s)
        assert status == "error"
        assert "boom" in detail

    def test_gsb_400_invalid(self):
        s = OsintSettings.load()
        s.gsb_api_key = "bad"
        with patch.object(gsb.requests, "post", return_value=_Resp(400)):
            assert gsb.probe(s)[0] == "invalid"

    def test_abusech_ok(self):
        s = OsintSettings.load()
        s.abusech_api_key = "k"
        with patch.object(abusech.requests, "post", return_value=_Resp(200)):
            assert abusech.probe(s)[0] == "ok"


# ---------------------------------------------------------------------------
# orchestratore
# ---------------------------------------------------------------------------

class TestOrchestrator:
    def test_saves_all_providers(self):
        s = OsintSettings.load()
        with patch.object(health, "_probes", return_value={p: (lambda _s: ("ok", "HTTP 200")) for p in KEYED_PROVIDERS}):
            result = check_enricher_health(s, save=True)
        assert set(result.keys()) == set(KEYED_PROVIDERS)
        assert all(v["status"] == "ok" for v in result.values())
        assert all("checked_at" in v for v in result.values())
        s.refresh_from_db()
        assert s.enricher_health["virustotal"]["status"] == "ok"

    def test_single_provider_preserves_others(self):
        s = OsintSettings.load()
        s.enricher_health = {"gsb": {"status": "invalid", "detail": "old", "checked_at": "2020-01-01"}}
        s.save(update_fields=["enricher_health"])
        with patch.object(health, "_probes", return_value={"virustotal": lambda _s: ("ok", "HTTP 200")}):
            result = check_enricher_health(s, providers=["virustotal"], save=True)
        assert result["virustotal"]["status"] == "ok"
        assert result["gsb"]["status"] == "invalid"  # preservato

    def test_probe_crash_is_contained(self):
        s = OsintSettings.load()
        def _boom(_s):
            raise RuntimeError("kaboom")
        with patch.object(health, "_probes", return_value={"virustotal": _boom}):
            result = check_enricher_health(s, providers=["virustotal"], save=False)
        assert result["virustotal"]["status"] == "error"
        assert "kaboom" in result["virustotal"]["detail"]


# ---------------------------------------------------------------------------
# task + endpoint
# ---------------------------------------------------------------------------

class TestTaskAndEndpoint:
    def test_task_skips_when_no_keys(self):
        from apps.osint.tasks import check_enricher_health as task
        s = OsintSettings.load()
        for p in KEYED_PROVIDERS:
            setattr(s, f"{p}_api_key", "")
        s.save()
        assert task() == {"checked": 0}

    def test_endpoint_test_keys(self):
        user = User.objects.create_superuser(username="h", password="p", email="h@t.com")
        client = APIClient()
        client.force_authenticate(user=user)
        with patch.object(health, "_probes", return_value={p: (lambda _s: ("ok", "HTTP 200")) for p in KEYED_PROVIDERS}):
            resp = client.post("/api/v1/osint/settings/test-keys/", {}, format="json")
        assert resp.status_code == 200
        assert resp.data["enricher_health"]["abusech"]["status"] == "ok"

    def test_endpoint_invalid_provider(self):
        user = User.objects.create_superuser(username="h2", password="p", email="h2@t.com")
        client = APIClient()
        client.force_authenticate(user=user)
        resp = client.post("/api/v1/osint/settings/test-keys/", {"provider": "nope"}, format="json")
        assert resp.status_code == 400

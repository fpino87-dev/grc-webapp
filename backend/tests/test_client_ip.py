"""
Test identificazione IP client proxy-aware (newfix 2026-06-09 #5).

Verifica `core.network.get_client_ip` e la presenza di NUM_PROXIES nella
config DRF: senza NUM_PROXIES il throttle usa l'X-Forwarded-For spoofabile
dal client (bypass del rate limit login); con NUM_PROXIES=1 conta solo
l'hop aggiunto dal proxy fidato.
"""
import pytest
from django.test import RequestFactory, override_settings

from core.network import get_client_ip

rf = RequestFactory()


def _drf(num_proxies):
    from django.conf import settings
    return {**settings.REST_FRAMEWORK, "NUM_PROXIES": num_proxies}


def test_num_proxies_configured_in_settings():
    from django.conf import settings
    assert "NUM_PROXIES" in settings.REST_FRAMEWORK


def test_no_xff_returns_remote_addr():
    request = rf.get("/", REMOTE_ADDR="10.0.0.5")
    assert get_client_ip(request) == "10.0.0.5"


def test_one_proxy_takes_last_xff_hop():
    # NPM appende l'IP reale del client in coda: l'ultimo hop è affidabile.
    request = rf.get(
        "/", REMOTE_ADDR="172.18.0.2",
        HTTP_X_FORWARDED_FOR="1.2.3.4, 203.0.113.7",
    )
    with override_settings(REST_FRAMEWORK=_drf(1)):
        assert get_client_ip(request) == "203.0.113.7"


def test_spoofed_xff_prefix_is_ignored():
    # Il client preprende valori arbitrari: con NUM_PROXIES=1 contano solo
    # gli hop appesi dal proxy fidato, lo spoof non cambia l'identità.
    spoofed = rf.get(
        "/", REMOTE_ADDR="172.18.0.2",
        HTTP_X_FORWARDED_FOR="6.6.6.6, 9.9.9.9, 203.0.113.7",
    )
    with override_settings(REST_FRAMEWORK=_drf(1)):
        assert get_client_ip(spoofed) == "203.0.113.7"


def test_zero_proxies_ignores_xff():
    request = rf.get(
        "/", REMOTE_ADDR="198.51.100.9",
        HTTP_X_FORWARDED_FOR="1.2.3.4",
    )
    with override_settings(REST_FRAMEWORK=_drf(0)):
        assert get_client_ip(request) == "198.51.100.9"


def test_two_proxies_takes_second_from_right():
    request = rf.get(
        "/", REMOTE_ADDR="172.18.0.2",
        HTTP_X_FORWARDED_FOR="203.0.113.7, 192.0.2.10",
    )
    with override_settings(REST_FRAMEWORK=_drf(2)):
        assert get_client_ip(request) == "203.0.113.7"


@pytest.mark.django_db
def test_audit_login_payload_uses_proxy_aware_ip():
    """L'audit di login deve loggare l'IP del client, non quello del proxy."""
    from django.contrib.auth import get_user_model
    from core.audit import AuditLog
    from core.jwt import _audit_login

    user = get_user_model().objects.create_user(
        username="ip@azienda.it", email="ip@azienda.it", password="x",
    )
    request = rf.post(
        "/api/token/", REMOTE_ADDR="172.18.0.2",
        HTTP_X_FORWARDED_FOR="203.0.113.7",
    )
    with override_settings(REST_FRAMEWORK=_drf(1)):
        _audit_login(user, success=True, request=request, extra={"path": "test"})

    log = AuditLog.objects.filter(action_code="auth.login.success").order_by("-timestamp_utc").first()
    assert log is not None
    assert log.payload["ip"] == "203.0.113.7"

"""Health check: DB e Redis (cache/throttle/broker) devono essere entrambi su."""
from unittest import mock

import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_ok_reports_db_and_cache():
    res = APIClient().get("/api/health/")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["db"] is True
    assert body["cache"] is True


@pytest.mark.django_db
def test_health_is_503_when_cache_is_down():
    """Regressione: con Redis giù login e API davano 500 ma l'health diceva ok."""
    with mock.patch("django.core.cache.cache.set", side_effect=ConnectionError("redis down")):
        res = APIClient().get("/api/health/")
    assert res.status_code == 503
    body = res.json()
    assert body["status"] == "error"
    assert body["db"] is True
    assert body["cache"] is False

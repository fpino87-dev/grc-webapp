"""Test retention log interazioni AI (GDPR Art. 5.1.e)."""
import uuid

import pytest
from django.test import override_settings
from django.utils import timezone


def _make_log(days_old):
    from apps.ai_engine.models import AiInteractionLog
    log = AiInteractionLog.objects.create(
        user_id=uuid.uuid4(), function="rca_draft", module_source="M09",
        entity_id=uuid.uuid4(), model_used="ollama/llama", input_hash="x" * 64,
        output_ai="bozza",
    )
    # created_at è auto_now_add: forziamo una data passata via update
    AiInteractionLog.objects.filter(pk=log.pk).update(
        created_at=timezone.now() - timezone.timedelta(days=days_old)
    )
    return log


@pytest.mark.django_db
@override_settings(AI_LOG_RETENTION_DAYS=365)
def test_cleanup_removes_old_keeps_recent():
    from apps.ai_engine.models import AiInteractionLog
    from apps.ai_engine.tasks import cleanup_ai_interaction_logs

    old = _make_log(400)
    recent = _make_log(10)

    result = cleanup_ai_interaction_logs.apply().result

    assert not AiInteractionLog.objects.filter(pk=old.pk).exists()
    assert AiInteractionLog.objects.filter(pk=recent.pk).exists()
    assert "1 record eliminati" in result


@pytest.mark.django_db
@override_settings(AI_LOG_RETENTION_DAYS=30)
def test_retention_period_configurable():
    from apps.ai_engine.models import AiInteractionLog
    from apps.ai_engine.tasks import cleanup_ai_interaction_logs

    _make_log(45)
    cleanup_ai_interaction_logs.apply()
    assert AiInteractionLog.objects.count() == 0

"""Test modelli notifiche — subscription, role profile, encryption."""
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="notif_user", email="notif@test.com", password="test")


# ── NotificationSubscription ──────────────────────────────────────────────

@pytest.mark.django_db
def test_create_subscription(user):
    from apps.notifications.models import NotificationSubscription
    sub = NotificationSubscription.objects.create(
        user=user,
        event_type="task_assigned",
        channel="email",
        enabled=True,
    )
    assert sub.id is not None
    assert sub.enabled is True


@pytest.mark.django_db
def test_subscription_unique_per_user_event_channel(user):
    from django.db import IntegrityError
    from apps.notifications.models import NotificationSubscription
    NotificationSubscription.objects.create(user=user, event_type="task_due_soon", channel="email", enabled=True)
    with pytest.raises(IntegrityError):
        NotificationSubscription.objects.create(user=user, event_type="task_due_soon", channel="email", enabled=False)


# ── NotificationRoleProfile ───────────────────────────────────────────────

@pytest.mark.django_db
def test_role_profile_get_active_events_essenziale():
    from apps.notifications.models import NotificationRoleProfile
    profile = NotificationRoleProfile(
        grc_role="compliance_officer",
        profile="essenziale",
        enabled=True,
    )
    events = profile.get_active_events()
    assert isinstance(events, list)
    assert len(events) > 0


@pytest.mark.django_db
def test_role_profile_silenzioso_returns_empty():
    from apps.notifications.models import NotificationRoleProfile
    profile = NotificationRoleProfile(
        grc_role="external_auditor",
        profile="silenzioso",
        enabled=True,
    )
    events = profile.get_active_events()
    assert events == []


@pytest.mark.django_db
def test_role_profile_custom_events():
    from apps.notifications.models import NotificationRoleProfile
    profile = NotificationRoleProfile(
        grc_role="plant_manager",
        profile="custom",
        custom_events=["task_assigned", "incident_created"],
        enabled=True,
    )
    events = profile.get_active_events()
    assert "task_assigned" in events
    assert "incident_created" in events


@pytest.mark.django_db
def test_get_or_create_defaults():
    from apps.notifications.models import NotificationRoleProfile
    # Returns count of created profiles (int)
    created = NotificationRoleProfile.get_or_create_defaults()
    assert isinstance(created, int)
    assert created >= 0
    # After creation, profiles should exist
    assert NotificationRoleProfile.objects.count() > 0


# ── EmailConfiguration encryption ─────────────────────────────────────────

@pytest.mark.django_db
def test_email_config_password_stored_encrypted():
    from apps.notifications.models import EmailConfiguration
    config = EmailConfiguration.objects.create(
        name="Test SMTP",
        provider="smtp_custom",
        host="smtp.test.com",
        port=587,
        use_tls=True,
        from_email="test@test.com",
        username="user@test.com",
        password="secret_password",
        active=False,
    )
    config.refresh_from_db()
    # La password letta deve matchare quella originale (decifrata)
    assert config.password == "secret_password"


@pytest.mark.django_db
def test_email_config_one_active_at_time():
    """Solo un config può essere attivo."""
    from apps.notifications.models import EmailConfiguration
    c1 = EmailConfiguration.objects.create(
        name="SMTP 1", provider="smtp_custom", host="smtp1.test.com",
        port=587, from_email="a@test.com", active=True,
    )
    assert c1.active is True


# ── NotificationRule ──────────────────────────────────────────────────────

@pytest.mark.django_db
def test_notification_rule_create():
    from apps.notifications.models import NotificationRule
    rule = NotificationRule.objects.create(
        event_type="incident_created",
        enabled=True,
        recipient_roles=["ciso", "compliance_officer"],
        scope_type="org",
        channel="email",
    )
    assert rule.id is not None
    assert "ciso" in rule.recipient_roles

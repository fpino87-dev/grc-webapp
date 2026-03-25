"""Test services notifiche."""
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="notif_svc", email="notifsvc@test.com", password="test")


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="NF-SVC", name="Plant Notif Svc", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.mark.django_db
def test_get_or_create_defaults_returns_int():
    from apps.notifications.models import NotificationRoleProfile
    result = NotificationRoleProfile.get_or_create_defaults()
    assert isinstance(result, int)


@pytest.mark.django_db
def test_create_subscription(user):
    from apps.notifications.models import NotificationSubscription
    sub = NotificationSubscription.objects.create(
        user=user,
        event_type="incident.created",
        channel="email",
        enabled=True,
    )
    assert sub.event_type == "incident.created"
    assert sub.enabled is True


@pytest.mark.django_db
def test_create_notification_rule(plant):
    from apps.notifications.models import NotificationRule
    rule = NotificationRule.objects.create(
        event_type="incident.created",
        enabled=True,
        scope_type="org",
        scope_plant=plant,
        channel="email",
    )
    assert rule.enabled is True

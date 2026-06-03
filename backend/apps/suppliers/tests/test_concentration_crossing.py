"""Test P2-4 follow-up — notifica M19 sul crossing di concentrazione critica."""
import pytest
from decimal import Decimal
from unittest.mock import patch

from apps.suppliers.models import Supplier
from apps.suppliers.services import check_concentration_crossing


pytestmark = pytest.mark.django_db


def _supplier(pct):
    return Supplier.objects.create(
        name="Acme", status="attivo",
        supply_concentration_pct=Decimal(str(pct)) if pct is not None else None,
    )


class TestCrossing:
    def test_fires_on_crossing_to_critical(self):
        sup = _supplier(60)  # > 50 → 'critica'
        with patch("apps.notifications.resolver.fire_notification") as fire:
            sent = check_concentration_crossing(sup)
        assert sent is True
        assert fire.called
        assert fire.call_args.args[0] == "supplier_concentration_critical"
        sup.refresh_from_db()
        assert sup.concentration_notified_threshold == "critica"

    def test_no_spam_when_already_notified(self):
        sup = _supplier(60)
        sup.concentration_notified_threshold = "critica"
        sup.save(update_fields=["concentration_notified_threshold"])
        with patch("apps.notifications.resolver.fire_notification") as fire:
            sent = check_concentration_crossing(sup)
        assert sent is False
        assert not fire.called

    def test_no_fire_below_critical(self):
        sup = _supplier(30)  # 'media'
        with patch("apps.notifications.resolver.fire_notification") as fire:
            sent = check_concentration_crossing(sup)
        assert sent is False
        assert not fire.called

    def test_reset_marker_when_drops_back(self):
        sup = _supplier(30)  # rientrata in 'media'
        sup.concentration_notified_threshold = "critica"
        sup.save(update_fields=["concentration_notified_threshold"])
        with patch("apps.notifications.resolver.fire_notification") as fire:
            check_concentration_crossing(sup)
        sup.refresh_from_db()
        assert sup.concentration_notified_threshold == ""  # reset → ri-notificabile
        assert not fire.called

    def test_recross_after_reset_fires_again(self):
        sup = _supplier(60)
        with patch("apps.notifications.resolver.fire_notification"):
            check_concentration_crossing(sup)
        # rientra (save completo: il pct va persistito, come fa il serializer)
        sup.supply_concentration_pct = Decimal("10")
        sup.save()
        with patch("apps.notifications.resolver.fire_notification"):
            check_concentration_crossing(sup)
        sup.refresh_from_db()
        assert sup.concentration_notified_threshold == ""
        # ri-attraversa
        sup.supply_concentration_pct = Decimal("70")
        sup.save()
        with patch("apps.notifications.resolver.fire_notification") as fire:
            sent = check_concentration_crossing(sup)
        assert sent is True
        assert fire.called


class TestInternalOnly:
    def test_external_auditor_excluded(self):
        from django.contrib.auth import get_user_model
        from apps.auth_grc.models import GrcRole, UserPlantAccess
        from apps.notifications.models import NotificationRoleProfile
        from apps.notifications.resolver import resolve_recipients

        User = get_user_model()
        NotificationRoleProfile.objects.create(
            grc_role=GrcRole.EXTERNAL_AUDITOR, profile="completo", enabled=True)
        ext = User.objects.create_user(username="ext@x.com", email="ext@x.com", password="x")
        UserPlantAccess.objects.create(user=ext, role=GrcRole.EXTERNAL_AUDITOR, scope_type="org")

        NotificationRoleProfile.objects.create(
            grc_role=GrcRole.RISK_MANAGER, profile="standard", enabled=True)
        rm = User.objects.create_user(username="rm@x.com", email="rm@x.com", password="x")
        UserPlantAccess.objects.create(user=rm, role=GrcRole.RISK_MANAGER, scope_type="org")

        recipients = resolve_recipients("supplier_concentration_critical")
        assert rm.email in recipients
        assert ext.email not in recipients

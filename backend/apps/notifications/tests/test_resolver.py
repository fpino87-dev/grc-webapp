"""P2-1 — copertura resolver notifiche (resolve_recipients + fire_notification)."""
import pytest
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model

from apps.auth_grc.models import GrcRole, UserPlantAccess
from apps.notifications.models import NotificationRoleProfile
from apps.notifications import resolver as R

pytestmark = pytest.mark.django_db
User = get_user_model()


def _user(email, role, scope_type="org", plants=None, bu=None):
    u = User.objects.create_user(username=email, email=email, password="x")
    acc = UserPlantAccess.objects.create(user=u, role=role, scope_type=scope_type, scope_bu=bu)
    if plants:
        acc.scope_plants.set(plants)
    return u, acc


def _profile(role, profile="completo"):
    return NotificationRoleProfile.objects.create(grc_role=role, profile=profile, enabled=True)


def _plant(code="RS-P", bu=None):
    from apps.plants.models import Plant
    return Plant.objects.create(code=code, name=code, country="IT",
                                nis2_scope="non_soggetto", status="attivo", bu=bu)


class TestResolveRecipients:
    def test_role_with_event_is_resolved(self):
        _profile(GrcRole.COMPLIANCE_OFFICER, "completo")
        u, _ = _user("co@x.it", GrcRole.COMPLIANCE_OFFICER)
        assert u.email in R.resolve_recipients("risk_red")

    def test_no_profile_no_recipients(self):
        # Nessun profilo abilitato → nessun destinatario
        assert R.resolve_recipients("risk_red") == []

    def test_disabled_profile_excluded(self):
        NotificationRoleProfile.objects.create(
            grc_role=GrcRole.COMPLIANCE_OFFICER, profile="completo", enabled=False)
        _user("co2@x.it", GrcRole.COMPLIANCE_OFFICER)
        assert R.resolve_recipients("risk_red") == []

    def test_event_not_in_profile_excluded(self):
        # 'silenzioso' non include alcun evento
        _profile(GrcRole.COMPLIANCE_OFFICER, "silenzioso")
        _user("co3@x.it", GrcRole.COMPLIANCE_OFFICER)
        assert R.resolve_recipients("risk_red") == []

    def test_inactive_user_excluded(self):
        _profile(GrcRole.COMPLIANCE_OFFICER, "completo")
        u, _ = _user("inactive@x.it", GrcRole.COMPLIANCE_OFFICER)
        u.is_active = False
        u.save(update_fields=["is_active"])
        assert u.email not in R.resolve_recipients("risk_red")

    def test_plant_scope_filters_out_of_scope_user(self):
        _profile(GrcRole.PLANT_MANAGER, "standard")
        p_in = _plant("IN")
        p_out = _plant("OUT")
        u_in, _ = _user("in@x.it", GrcRole.PLANT_MANAGER, scope_type="single_plant", plants=[p_in])
        u_out, _ = _user("out@x.it", GrcRole.PLANT_MANAGER, scope_type="single_plant", plants=[p_out])
        recipients = R.resolve_recipients("risk_red", plant=p_in)
        assert u_in.email in recipients
        assert u_out.email not in recipients

    def test_internal_only_event_strips_external_role(self):
        _profile(GrcRole.EXTERNAL_AUDITOR, "completo")
        ext, _ = _user("ext@third.it", GrcRole.EXTERNAL_AUDITOR)
        _profile(GrcRole.COMPLIANCE_OFFICER, "completo")
        internal, _ = _user("int@x.it", GrcRole.COMPLIANCE_OFFICER)
        rec = R.resolve_recipients("osint_critical")
        assert internal.email in rec
        assert ext.email not in rec


class TestUserHasAccess:
    def test_org_scope_sees_all(self):
        acc = SimpleNamespace(scope_type="org", scope_bu=None)
        assert R._user_has_access_to_plant(acc, _plant("ORG")) is True

    def test_bu_scope_matches_plant_bu(self):
        from apps.plants.models import BusinessUnit
        bu = BusinessUnit.objects.create(name="BU1", code="BU1")
        p = _plant("BUP", bu=bu)
        acc = SimpleNamespace(scope_type="bu", scope_bu=bu)
        assert R._user_has_access_to_plant(acc, p) is True
        acc2 = SimpleNamespace(scope_type="bu", scope_bu=BusinessUnit.objects.create(name="BU2", code="BU2"))
        assert R._user_has_access_to_plant(acc2, p) is False


class TestFireNotification:
    def _setup(self, event, role=GrcRole.COMPLIANCE_OFFICER):
        _profile(role, "completo")
        _user(f"{event}@x.it", role)

    def test_no_recipients_short_circuits(self):
        with patch("apps.notifications.services.notify_risk_red") as m:
            R.fire_notification("risk_red", context={"assessment": object()})
        assert not m.called  # nessun profilo → niente invio

    def test_dispatch_risk_red(self):
        self._setup("riskred")
        with patch("apps.notifications.services.notify_risk_red") as m:
            R.fire_notification("risk_red", context={"assessment": object()})
        assert m.called

    def test_dispatch_incident_nis2(self):
        self._setup("inc")
        with patch("apps.notifications.services.notify_incident_nis2") as m:
            R.fire_notification("incident_nis2", context={"incident": object()})
        assert m.called

    def test_dispatch_bcp_test_failed_uses_send_email(self):
        self._setup("bcp")
        plan = SimpleNamespace(title="Piano X")
        with patch("apps.notifications.services.send_grc_email") as m:
            R.fire_notification("bcp_test_failed", plant=_plant("BCPF"), context={"plan": plan})
        assert m.called

    def test_unknown_event_no_crash(self):
        self._setup("unk")
        # evento mappato a un profilo ma senza branch in fire_notification → no-op
        R.fire_notification("role_vacant", context={})

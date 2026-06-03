"""Test P2-3 — notifiche M19 su alert OSINT critici (solo personale interno)."""
import pytest
from unittest.mock import patch

from django.contrib.auth import get_user_model

from apps.auth_grc.models import GrcRole, UserPlantAccess
from apps.notifications.models import NotificationRoleProfile
from apps.notifications.resolver import resolve_recipients
from apps.osint.alerts import run_alerts, _entity_plant
from apps.osint.models import (
    AlertSeverity, AlertType, EntityType, OsintEntity, OsintScan,
    ScanStatus, SourceModule,
)
from apps.plants.models import Plant


pytestmark = pytest.mark.django_db

User = get_user_model()


def _plant():
    return Plant.objects.create(code="NT1", name="Notify Plant", country="IT",
                                nis2_scope="essenziale", status="attivo")


def _user_with_role(email, role):
    u = User.objects.create_user(username=email, email=email, password="x")
    UserPlantAccess.objects.create(user=u, role=role, scope_type="org")
    return u


def _profile(role, profile="completo"):
    return NotificationRoleProfile.objects.create(grc_role=role, profile=profile, enabled=True)


# ---------------------------------------------------------------------------
# Guardia "solo interni": i ruoli esterni non ricevono mai osint_critical
# ---------------------------------------------------------------------------

class TestInternalOnlyGuard:
    def test_external_auditor_excluded_even_if_profile_includes_event(self):
        # external_auditor con profilo "completo" (che include osint_critical)
        _profile(GrcRole.EXTERNAL_AUDITOR, "completo")
        ext = _user_with_role("ext-auditor@thirdparty.com", GrcRole.EXTERNAL_AUDITOR)
        # un interno con lo stesso profilo
        _profile(GrcRole.COMPLIANCE_OFFICER, "completo")
        internal = _user_with_role("ciso@azienda.it", GrcRole.COMPLIANCE_OFFICER)

        recipients = resolve_recipients("osint_critical")
        assert internal.email in recipients
        assert ext.email not in recipients

    def test_other_events_still_reach_external_when_configured(self):
        # Sanity: la guardia è limitata a osint_critical, non rompe gli altri eventi.
        _profile(GrcRole.EXTERNAL_AUDITOR, "completo")
        ext = _user_with_role("ext2@thirdparty.com", GrcRole.EXTERNAL_AUDITOR)
        recipients = resolve_recipients("finding_major")
        assert ext.email in recipients


# ---------------------------------------------------------------------------
# Dispatch dal motore alert: solo CRITICAL, best-effort su on_commit
# ---------------------------------------------------------------------------

def _scan(entity, **kw):
    return OsintScan.objects.create(
        entity=entity, status=ScanStatus.COMPLETED,
        ssl_valid=kw.get("ssl_valid", True), ssl_days_remaining=kw.get("ssl_days_remaining", 120),
        spf_present=True, dmarc_present=True, dmarc_policy="reject", mx_present=True,
        gsb_status="safe", in_blacklist=kw.get("in_blacklist", False),
        blacklist_sources=kw.get("blacklist_sources", []),
        vt_malicious=0, abuseipdb_score=0, otx_pulses=0, hibp_breaches=0,
        score_total=kw.get("score_total", 10),
    )


class TestCriticalDispatch:
    def test_critical_alert_fires_notification(self, django_capture_on_commit_callbacks):
        from apps.osint.models import OsintSettings
        s = OsintSettings.load()
        p = _plant()
        entity = OsintEntity.objects.create(
            entity_type=EntityType.MY_DOMAIN, source_module=SourceModule.SITES,
            source_id=p.id, domain="crit.example.com", display_name="Crit",
        )
        # score critico → alert CRITICAL
        scan = _scan(entity, score_total=85)
        with patch("apps.notifications.resolver.fire_notification") as mock_fire:
            with django_capture_on_commit_callbacks(execute=True):
                alerts = run_alerts(entity, scan, s)
        assert any(a.severity == AlertSeverity.CRITICAL for a in alerts)
        # fire_notification chiamato con osint_critical e il plant risolto
        assert mock_fire.called
        call = mock_fire.call_args
        assert call.args[0] == "osint_critical"
        assert call.kwargs["plant"] == p
        assert call.kwargs["context"]["entity"] == entity

    def test_no_notification_when_only_non_critical(self, django_capture_on_commit_callbacks):
        from apps.osint.models import OsintSettings
        s = OsintSettings.load()
        p = _plant()
        entity = OsintEntity.objects.create(
            entity_type=EntityType.MY_DOMAIN, source_module=SourceModule.SITES,
            source_id=p.id, domain="ok.example.com", display_name="Ok",
        )
        scan = _scan(entity, score_total=10)  # niente trigger
        with patch("apps.notifications.resolver.fire_notification") as mock_fire:
            with django_capture_on_commit_callbacks(execute=True):
                run_alerts(entity, scan, s)
        assert not mock_fire.called


class TestEntityPlant:
    def test_my_domain_resolves_plant(self):
        p = _plant()
        entity = OsintEntity.objects.create(
            entity_type=EntityType.MY_DOMAIN, source_module=SourceModule.SITES,
            source_id=p.id, domain="d.example.com", display_name="D",
        )
        assert _entity_plant(entity) == p

    def test_supplier_returns_none(self):
        entity = OsintEntity.objects.create(
            entity_type=EntityType.SUPPLIER, source_module=SourceModule.SUPPLIERS,
            source_id=_plant().id, domain="s.example.com", display_name="S",
        )
        assert _entity_plant(entity) is None

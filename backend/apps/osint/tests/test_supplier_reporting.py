"""Fornitori "da segnalare" (non da correggere), voto A–F, postura esterna,
riepilogo settimanale e postura per la scheda fornitore."""
import datetime
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.osint.models import (
    EntityType, FindingStatus, OsintEntity, OsintFinding, OsintScan, ScanStatus, SourceModule,
)

User = get_user_model()
pytestmark = pytest.mark.django_db

URL = "/api/v1/osint/"


@pytest.fixture
def client(db):
    u = User.objects.create_superuser(username="osrep", password="x", email="osrep@test.com")
    c = APIClient()
    c.force_authenticate(user=u)
    return c


def _entity(kind, domain, risk=None, source_id=None):
    module = {EntityType.SUPPLIER: SourceModule.SUPPLIERS, EntityType.MY_DOMAIN: SourceModule.SITES,
              EntityType.ASSET: SourceModule.ASSETS_IT}[kind]
    e = OsintEntity.objects.create(entity_type=kind, source_module=module, source_id=source_id or uuid.uuid4(),
                                   domain=domain, display_name=domain, last_score_total=risk,
                                   last_scan_at=timezone.now() if risk is not None else None)
    if risk is not None:
        OsintScan.objects.create(entity=e, status=ScanStatus.COMPLETED, score_total=risk)
    return e


def _finding(entity, code="ssl_expired", severity="critical", **kw):
    return OsintFinding.objects.create(entity=entity, code=code, severity=severity, **kw)


def test_grade_and_security_follow_thresholds():
    from apps.osint.scoring import grade_for, security_score
    assert security_score(20) == 80 and security_score(None) is None
    assert [grade_for(r) for r in (5, 20, 35, 55, 80)] == ["A", "B", "C", "D", "F"]


def test_supplier_finding_is_reported_and_followed_up(client):
    sup = _entity(EntityType.SUPPLIER, "fornitore.example.com", risk=80)
    f = _finding(sup)
    resp = client.post(f"{URL}findings/{f.pk}/report/", {"note": "mail al referente IT"}, format="json")
    assert resp.status_code == 200, resp.data
    assert resp.data["status"] == "reported" and resp.data["reported_by_name"] == "osrep"
    assert resp.data["report_overdue"] is False
    OsintFinding.objects.filter(pk=f.pk).update(reported_at=timezone.now() - datetime.timedelta(days=31))
    f.refresh_from_db()
    from apps.osint.findings import report_overdue
    assert report_overdue(f) is True


def test_own_findings_are_not_reported(client):
    own = _entity(EntityType.MY_DOMAIN, "azienda.example.com", risk=10)
    f = _finding(own)
    assert client.post(f"{URL}findings/{f.pk}/report/", {}, format="json").status_code == 400


def test_reported_finding_auto_resolves_when_no_longer_detected():
    from apps.osint.findings import sync_findings
    sup = _entity(EntityType.SUPPLIER, "fornitore2.example.com", risk=10)
    f = _finding(sup, code="blacklist", status=FindingStatus.REPORTED, reported_at=timezone.now())
    clean = OsintScan.objects.create(entity=sup, status=ScanStatus.COMPLETED, score_total=0, in_blacklist=False)
    sync_findings(sup, clean)
    f.refresh_from_db()
    assert f.status == FindingStatus.RESOLVED


def test_findings_ownership_filter(client):
    own = _entity(EntityType.MY_DOMAIN, "a.example.com", risk=10)
    sup = _entity(EntityType.SUPPLIER, "b.example.com", risk=10)
    _finding(own)
    _finding(sup)
    own_rows = client.get(f"{URL}findings/", {"ownership": "own"}).data
    sup_rows = client.get(f"{URL}findings/", {"ownership": "supplier"}).data
    assert [r["entity_domain"] for r in own_rows] == ["a.example.com"]
    assert [r["entity_domain"] for r in sup_rows] == ["b.example.com"]


def test_posture_counts_own_and_supplier_reports(client):
    own = _entity(EntityType.MY_DOMAIN, "c.example.com", risk=20)
    _finding(own)
    _finding(own, code="dkim_missing", severity="warning")
    sup = _entity(EntityType.SUPPLIER, "d.example.com", risk=80)
    _finding(sup)
    _finding(sup, code="blacklist", status=FindingStatus.REPORTED,
             reported_at=timezone.now() - datetime.timedelta(days=40))
    data = client.get(f"{URL}dashboard/posture/").data
    assert data["security"] == 80 and data["grade"] == "B"
    assert data["own"]["critical"] == 1 and data["own"]["warning"] == 1
    assert data["suppliers"] == {"to_report": 1, "reported_open": 1, "overdue": 1}
    assert data["trend"] and data["trend"][-1]["security"] == 80


def test_weekly_changes(client):
    own = _entity(EntityType.MY_DOMAIN, "e.example.com", risk=40)
    OsintEntity.objects.filter(pk=own.pk).update(prev_score_total=10)
    _finding(own)
    sup = _entity(EntityType.SUPPLIER, "f.example.com", risk=80)
    _finding(sup)
    data = client.get(f"{URL}dashboard/changes/").data
    assert data["new_own"]["count"] == 1 and data["new_supplier_critical"]["count"] == 1
    assert data["score_changes"][0]["delta"] == -30


def test_entity_list_and_detail_expose_grade_findings_and_trend(client):
    own = _entity(EntityType.MY_DOMAIN, "g.example.com", risk=55)
    _finding(own)
    row = next(r for r in client.get(f"{URL}entities/").data if r["domain"] == "g.example.com")
    assert row["grade"] == "D" and row["security"] == 45
    assert row["open_findings"] == {"critical": 1, "warning": 0, "info": 0}
    assert row["trend"] == [45]
    detail = client.get(f"{URL}entities/{own.pk}/").data
    assert [f["code"] for f in detail["findings"]] == ["ssl_expired"]
    assert "events" in detail


def test_supplier_posture_for_supplier_card(client):
    sid = uuid.uuid4()
    sup = _entity(EntityType.SUPPLIER, "h.example.com", risk=75, source_id=sid)
    _finding(sup, status=FindingStatus.REPORTED, reported_at=timezone.now(), report_note="segnalato")
    data = client.get(f"{URL}entities/by-supplier/{sid}/").data
    assert data[0]["grade"] == "F" and data[0]["critical_open"][0]["status"] == "reported"
    assert data[0]["reports"][0]["note"] == "segnalato"

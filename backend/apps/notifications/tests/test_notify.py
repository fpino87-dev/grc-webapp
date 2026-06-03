"""P2-1 — copertura funzioni notify_* (formattazione email) di notifications.services."""
import datetime
from types import SimpleNamespace
from unittest.mock import patch

from apps.notifications import services as S

REC = ["a@x.it", "b@x.it"]


def _ns(**kw):
    return SimpleNamespace(**kw)


def _call(fn, *args):
    """Esegue una notify_* mockando send_grc_email; ritorna i kwargs passati."""
    with patch.object(S, "send_grc_email") as m:
        fn(*args)
    assert m.called, f"{fn.__name__} non ha chiamato send_grc_email"
    return m.call_args


def test_notify_task_assigned():
    task = _ns(title="T", priority="alta", due_date=None, plant=_ns(name="P1"))
    _call(S.notify_task_assigned, task, "u@x.it")


def test_notify_finding_major():
    finding = _ns(title="NC1", auditor_name="Mario", response_deadline="2026-07-01",
                  audit_prep=_ns(plant=_ns(name="P1")))
    _call(S.notify_finding_major, finding, REC)


def test_notify_risk_red():
    asset = _ns(name="Server")
    assessment = _ns(name="R1", asset=asset, plant=_ns(name="P1"), score=20)
    _call(S.notify_risk_red, assessment, REC)


def test_notify_incident_nis2():
    inc = _ns(title="Inc", severity="critica", detected_at="2026-06-01", plant=_ns(name="P1"))
    _call(S.notify_incident_nis2, inc, REC)


def test_notify_role_expiring():
    user = _ns(get_full_name=lambda: "Mario Rossi", email="m@x.it")
    assignment = _ns(role="ciso", user=user, valid_until="2026-07-01")
    _call(S.notify_role_expiring, assignment, 15, REC)


def test_notify_evidence_expired():
    control = _ns(external_id="A.5.1", get_title=lambda lang: "Controllo")
    instance = _ns(control=control, plant=_ns(name="P1"))
    _call(S.notify_evidence_expired, instance, REC)


def test_notify_document_approval_and_review_and_broadcast():
    doc = _ns(title="Doc", document_type="policy", plant=_ns(name="P1"), approved_at="2026-06-01")
    _call(S.notify_document_approval_needed, doc, REC)
    _call(S.notify_document_review_needed, doc, REC)
    _call(S.notify_document_approved_broadcast, doc, REC)


def test_notify_kpi_alert():
    kpi = _ns(name="MTTR", kpi_code="mttr", unit="ore")
    snap = _ns(status="critical", value=12, week_start="2026-W23")
    _call(S.notify_kpi_alert, kpi, _ns(name="P1"), snap, REC)


def test_notify_kpi_alert_global_plant_none():
    kpi = _ns(name="MTTR", kpi_code="mttr", unit="ore")
    snap = _ns(status="warning", value=None, week_start="2026-W23")
    _call(S.notify_kpi_alert, kpi, None, snap, REC)


def test_notify_osint_alert():
    alert = _ns(get_alert_type_display=lambda: "SSL scaduto",
                get_severity_display=lambda: "Critico", description="dettagli")
    entity = _ns(display_name="ACME", domain="acme.com")
    _call(S.notify_osint_alert, alert, entity, REC)


def test_notify_supplier_concentration():
    sup = _ns(name="Fornitore X", supply_concentration_pct=60, nis2_relevant=True)
    _call(S.notify_supplier_concentration, sup, REC)


def test_send_grc_email_empty_recipients_returns_false(db):
    assert S.send_grc_email("subj", "body", []) is False

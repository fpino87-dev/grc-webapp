"""Snapshot: azioni precedenti, KPI, audit, riesame di organizzazione, scadenzario."""
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.management_review.models import ManagementReview, ReviewAction
from apps.management_review.services import generate_snapshot

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def user(db):
    return User.objects.create_user(username="snapb", email="snapb@x.it", password="x")


def _plant(code):
    from apps.plants.models import Plant
    return Plant.objects.create(code=code, name=f"Plant {code}", country="IT", nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def plant(db):
    return _plant("SB-1")


def _review(plant, user, date, **kw):
    return ManagementReview.objects.create(plant=plant, title=f"Riesame {date}", review_date=date,
                                           created_by=user, **kw)


def test_previous_actions_block(plant, user):
    today = timezone.localdate()
    old = _review(plant, user, today - datetime.timedelta(days=800))
    prev = _review(plant, user, today - datetime.timedelta(days=365))
    current = _review(plant, user, today)
    ReviewAction.objects.create(review=old, description="Vecchia aperta", status="aperto",
                                due_date=today - datetime.timedelta(days=10))
    ReviewAction.objects.create(review=old, description="Vecchia chiusa prima", status="chiuso",
                                closed_at=timezone.now() - datetime.timedelta(days=500))
    ReviewAction.objects.create(review=prev, description="Precedente chiusa", status="chiuso", closed_at=timezone.now())
    ReviewAction.objects.create(review=prev, description="Precedente aperta", status="aperto",
                                due_date=today + datetime.timedelta(days=10))
    ReviewAction.objects.create(review=current, description="Di questo riesame")

    block = generate_snapshot(current, user)["azioni_precedenti"]
    assert block["riesame_precedente"]["id"] == str(prev.pk)
    assert block["totale"] == 3 and block["aperte"] == 2 and block["scadute"] == 1 and block["chiuse"] == 1
    assert block["elenco"][0]["description"] == "Vecchia aperta" and block["elenco"][0]["overdue"] is True


def test_first_review_has_no_previous_actions(plant, user):
    block = generate_snapshot(_review(plant, user, timezone.localdate()), user)["azioni_precedenti"]
    assert block["riesame_precedente"] is None and block["elenco"] == []


def test_kpi_and_audit_blocks(plant, user):
    from apps.audit_prep.models import AuditFinding, AuditPrep
    from apps.tasks.models import KPIDefinition, OperationalKpiSnapshot

    kpi = KPIDefinition.objects.create(
        kpi_code="patch_rate", name="Patch entro SLA", unit="%", source="checklist", aggregation="success_rate",
        plant=plant, threshold_warning=90, threshold_critical=80, threshold_direction="above", is_active=True,
    )
    OperationalKpiSnapshot.objects.create(kpi_definition=kpi, plant=plant, week_start=datetime.date(2026, 5, 18),
                                          value=70.0, status="critical", source="checklist")
    today = timezone.localdate()
    prep = AuditPrep.objects.create(plant=plant, title="Audit TISAX", audit_date=today - datetime.timedelta(days=30),
                                    readiness_score=82)
    AuditFinding.objects.create(audit_prep=prep, finding_type="minor_nc", title="Log non conservati", description="x",
                                audit_date=today, response_deadline=today - datetime.timedelta(days=1))
    AuditFinding.objects.create(audit_prep=prep, finding_type="major_nc", title="Nessun test restore", description="x",
                                audit_date=today)
    AuditFinding.objects.create(audit_prep=prep, finding_type="opportunity", title="Automatizzare report",
                                description="x", audit_date=today)

    snap = generate_snapshot(_review(plant, user, today), user)
    assert snap["kpi"]["attenzione"] == 1
    assert snap["kpi"]["elenco_attenzione"][0]["name"] == "Patch entro SLA"
    audit = snap["audit"]
    assert audit["audit_12m"] == 1 and audit["nc_aperte_maggiori"] == 1 and audit["nc_aperte_minori"] == 1
    assert audit["finding_scaduti"] == 1 and audit["opportunita_aperte"] == 1
    assert [f["title"] for f in audit["elenco_nc_aperte"]] == ["Nessun test restore", "Log non conservati"]
    assert audit["elenco_audit"][0]["readiness_score"] == 82


def test_org_wide_review_aggregates_all_sites(user):
    from apps.incidents.models import Incident

    p1, p2 = _plant("SB-A"), _plant("SB-B")
    for p in (p1, p2):
        Incident.objects.create(plant=p, title=f"Inc {p.code}", description="x", detected_at=timezone.now(),
                                severity="alta", status="aperto")
    snap = generate_snapshot(_review(None, user, timezone.localdate()), user)
    assert snap["incidenti"]["aperti"] == 2
    sites = {s["code"]: s for s in snap["siti"]}
    assert sites["SB-A"]["incidenti_aperti"] == 1 and sites["SB-B"]["incidenti_aperti"] == 1


def test_schedule_includes_planned_and_next_review(plant, user):
    from apps.compliance_schedule.services import get_activity_schedule

    today = timezone.localdate()
    done = _review(plant, user, today - datetime.timedelta(days=300), status="completato",
                   next_review_date=today + datetime.timedelta(days=65))
    items = [i for i in get_activity_schedule(plant=plant, months_ahead=6) if i["category"] == "management_review"]
    assert len(items) == 1 and items[0]["due_date"] == str(done.next_review_date)

    planned = _review(plant, user, today + datetime.timedelta(days=60))
    items = [i for i in get_activity_schedule(plant=plant, months_ahead=6) if i["category"] == "management_review"]
    assert [i["ref_id"] for i in items] == [str(planned.pk)]

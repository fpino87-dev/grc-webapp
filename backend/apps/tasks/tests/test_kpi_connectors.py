"""Test connettori KPI interni (source="internal"): calcolo dai dati dei moduli
GRC, dispatch via compute_and_store_kpi_snapshot e coerenza col catalogo."""
import datetime

import pytest
from django.utils import timezone


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="KPI-C", name="Plant Conn", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


def _monday():
    from apps.tasks.services import _monday_of
    return _monday_of(timezone.localdate())


# ── M03 Controlli ────────────────────────────────────────────────────────────
@pytest.fixture
def framework(db):
    from apps.controls.models import Framework
    return Framework.objects.create(
        code="ISO27001", name="ISO 27001", version="2022",
        published_at=datetime.date(2022, 10, 1),
    )


def _control(framework, ext_id):
    from apps.controls.models import Control
    return Control.objects.create(
        framework=framework, external_id=ext_id, translations={"it": {"text": ext_id}}
    )


@pytest.mark.django_db
def test_controls_compliance_rate(plant, framework):
    from apps.controls.models import ControlInstance
    from apps.tasks.kpi_connectors import controls_compliance_rate

    # 2 compliant + 1 gap = denominatore 3; na ed escluso fuori dal denominatore
    for i, status in enumerate(["compliant", "compliant", "gap"]):
        ControlInstance.objects.create(plant=plant, control=_control(framework, f"A.{i}"), status=status)
    ControlInstance.objects.create(plant=plant, control=_control(framework, "A.na"), status="na")
    ControlInstance.objects.create(
        plant=plant, control=_control(framework, "A.excl"),
        status="compliant", applicability="escluso",
    )

    res = controls_compliance_rate(plant, _monday())
    assert res["run_count"] == 3
    assert res["value"] == 66.67  # 2/3


# ── M07 Evidenze ──────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_evidence_expiry_rate(plant):
    from apps.documents.models import Evidence
    from apps.tasks.kpi_connectors import evidence_expiry_rate

    today = timezone.localdate()
    Evidence.objects.create(title="perenne", plant=plant, valid_until=None)
    Evidence.objects.create(title="valida", plant=plant, valid_until=today + datetime.timedelta(days=30))
    Evidence.objects.create(title="scaduta", plant=plant, valid_until=today - datetime.timedelta(days=1))

    res = evidence_expiry_rate(plant, _monday())
    assert res["run_count"] == 3
    assert res["value"] == 66.67  # 2/3 valide


# ── M11 PDCA ──────────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_open_pdca_over_90days(plant):
    from apps.pdca.models import PdcaCycle
    from apps.tasks.kpi_connectors import open_pdca_over_90days

    old = PdcaCycle.objects.create(plant=plant, title="vecchio", trigger_type="manual", fase_corrente="do")
    # created_at è auto_now_add: backdate via update per simulare >90 giorni
    PdcaCycle.objects.filter(pk=old.pk).update(
        created_at=timezone.now() - datetime.timedelta(days=120)
    )
    PdcaCycle.objects.create(plant=plant, title="recente", trigger_type="manual", fase_corrente="plan")
    closed = PdcaCycle.objects.create(plant=plant, title="chiuso", trigger_type="manual", fase_corrente="chiuso")
    PdcaCycle.objects.filter(pk=closed.pk).update(
        created_at=timezone.now() - datetime.timedelta(days=120)
    )

    res = open_pdca_over_90days(plant, _monday())
    assert res["value"] == 1.0


# ── M17 Audit findings ────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_audit_findings_open_rate(plant, framework):
    from apps.audit_prep.models import AuditFinding, AuditPrep
    from apps.tasks.kpi_connectors import audit_findings_open_rate

    prep = AuditPrep.objects.create(plant=plant, framework=framework, title="Audit 2026")
    today = timezone.localdate()
    for st in ["open", "in_response", "closed", "accepted_by_auditor"]:
        AuditFinding.objects.create(
            audit_prep=prep, finding_type="minor_nc", title=f"f-{st}",
            description="x", audit_date=today, status=st,
        )

    res = audit_findings_open_rate(plant, _monday())
    assert res["run_count"] == 4
    assert res["value"] == 50.0  # open + in_response su 4


# ── M15 Training ──────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_training_completion_rate(plant):
    from django.contrib.auth import get_user_model

    from apps.tasks.kpi_connectors import training_completion_rate
    from apps.training.models import TrainingCourse, TrainingEnrollment
    User = get_user_model()

    course = TrainingCourse.objects.create(title="Awareness", mandatory=True, status="attivo")
    course.plants.add(plant)
    for i, st in enumerate(["completato", "completato", "in_corso", "assegnato"]):
        u = User.objects.create_user(username=f"tu{i}", email=f"tu{i}@t.com", password="x")
        TrainingEnrollment.objects.create(course=course, user=u, status=st)

    res = training_completion_rate(plant, _monday())
    assert res["run_count"] == 4
    assert res["value"] == 50.0


# ── M04 Asset EOL ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_systems_eol_count(plant):
    from apps.assets.models import AssetIT
    from apps.tasks.kpi_connectors import systems_eol_count

    today = timezone.localdate()
    AssetIT.objects.create(plant=plant, name="srv1", asset_type="IT", eol_date=today - datetime.timedelta(days=1))
    AssetIT.objects.create(plant=plant, name="srv2", asset_type="IT", eol_date=today - datetime.timedelta(days=400))
    AssetIT.objects.create(plant=plant, name="srv3", asset_type="IT", eol_date=today + datetime.timedelta(days=10))
    AssetIT.objects.create(plant=plant, name="srv4", asset_type="IT", eol_date=None)

    res = systems_eol_count(plant, _monday())
    assert res["value"] == 2.0


# ── M09 Incidenti ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_incident_mttr_hours(plant):
    from apps.incidents.models import Incident
    from apps.tasks.kpi_connectors import incident_mttr_hours

    week = _monday()
    base = timezone.make_aware(datetime.datetime.combine(week, datetime.time(9, 0)))
    Incident.objects.create(
        plant=plant, title="i1", description="x", severity="media", status="chiuso",
        detected_at=base, closed_at=base + datetime.timedelta(hours=4),
    )
    Incident.objects.create(
        plant=plant, title="i2", description="x", severity="alta", status="chiuso",
        detected_at=base, closed_at=base + datetime.timedelta(hours=6),
    )
    res = incident_mttr_hours(plant, week)
    assert res["run_count"] == 2
    assert res["value"] == 5.0  # media (4h, 6h)


@pytest.mark.django_db
def test_incident_recurrence_rate(plant):
    from apps.incidents.models import Incident
    from apps.tasks.kpi_connectors import incident_recurrence_rate

    week = _monday()
    base = timezone.make_aware(datetime.datetime.combine(week, datetime.time(10, 0)))
    for i in range(4):
        Incident.objects.create(
            plant=plant, title=f"r{i}", description="x", severity="bassa",
            detected_at=base, is_recurrent=(i == 0),
        )
    res = incident_recurrence_rate(plant, week)
    assert res["run_count"] == 4
    assert res["value"] == 25.0


# ── M14 Fornitori ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_suppliers_assessed_and_unassessed(plant):
    from apps.suppliers.models import Supplier, SupplierAssessment
    from apps.tasks.kpi_connectors import suppliers_assessed_rate, suppliers_critical_unassessed

    today = timezone.localdate()
    s1 = Supplier.objects.create(name="critico-ok", risk_level="critico", status="attivo")
    s1.plants.add(plant)
    SupplierAssessment.objects.create(
        supplier=s1, assessment_date=today, status="approvato",
        next_assessment_date=today + datetime.timedelta(days=200),
    )
    s2 = Supplier.objects.create(name="critico-ko", risk_level="critico", status="attivo")
    s2.plants.add(plant)
    # fornitore non critico: fuori dal perimetro
    s3 = Supplier.objects.create(name="medio", risk_level="medio", status="attivo")
    s3.plants.add(plant)

    assert suppliers_assessed_rate(plant, _monday())["value"] == 50.0
    assert suppliers_critical_unassessed(plant, _monday())["value"] == 1.0


# ── Dispatch + catalogo ───────────────────────────────────────────────────────
@pytest.mark.django_db
def test_compute_and_store_dispatches_internal(plant, framework):
    from apps.controls.models import ControlInstance
    from apps.tasks.models import KPIDefinition, OperationalKpiSnapshot
    from apps.tasks.services import compute_and_store_kpi_snapshot

    ControlInstance.objects.create(plant=plant, control=_control(framework, "B.1"), status="compliant")
    kpi = KPIDefinition.objects.create(
        kpi_code="controls_compliance_rate", name="Conformità controlli", unit="%",
        source="internal", aggregation="last_value", plant=plant,
        threshold_warning=85.0, threshold_critical=70.0, threshold_direction="above",
    )
    snap = compute_and_store_kpi_snapshot(kpi, plant, _monday())
    assert snap.value == 100.0
    assert snap.status == "ok"
    assert snap.source == "internal"
    assert OperationalKpiSnapshot.objects.filter(kpi_definition=kpi).count() == 1


def test_catalog_marks_connector_codes_internal():
    from apps.tasks.kpi_catalog import KPI_CATALOG
    from apps.tasks.kpi_connectors import INTERNAL_CONNECTORS

    for code in INTERNAL_CONNECTORS:
        assert code in KPI_CATALOG, f"{code} assente dal catalogo"
        assert KPI_CATALOG[code]["source"] == "internal", f"{code} non marcato internal"

"""BCP — approvazione e test separati, copertura a tre stati, RTO dimostrato."""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bcp import services
from apps.bcp.models import BcpPlan

User = get_user_model()
URL_PLANS = "/api/v1/bcp/plans/"
URL_TESTS = "/api/v1/bcp/tests/"


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess

    u = User.objects.create_user(username="bcp_srv", email="bcp_srv@test.com", password="test")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _plant(code):
    from apps.plants.models import Plant

    return Plant.objects.create(code=code, name=f"Plant {code}", country="IT",
                                nis2_scope="importante", status="attivo")


@pytest.fixture
def plant(db):
    return _plant("BCS")


@pytest.fixture
def process(plant):
    from apps.bia.models import CriticalProcess

    return CriticalProcess.objects.create(plant=plant, name="Stampaggio", criticality=5,
                                          rto_target_hours=8, rpo_target_hours=4, mtpd_hours=24)


def _plan(plant, user, process=None, **kw):
    plan = BcpPlan.objects.create(plant=plant, title=kw.pop("title", "Piano"), created_by=user, **kw)
    if process is not None:
        plan.critical_processes.add(process)
    return plan


# ── Test e approvazione separati ─────────────────────────────────────────────

@pytest.mark.django_db
def test_test_on_approved_plan_keeps_approval(plant, user, process):
    plan = _plan(plant, user, process, status="approvato", test_frequency_value=1,
                 test_frequency_unit="years")
    test, warnings = services.record_test(plan, "superato", user, rto_achieved=6)
    plan.refresh_from_db()
    assert plan.status == "approvato"
    assert plan.last_test_date == test.test_date
    assert plan.next_test_date == services.add_duration(test.test_date, 1, "years")
    assert warnings == []


@pytest.mark.django_db
def test_past_test_date_and_older_test_does_not_move_dates(plant, user):
    plan = _plan(plant, user, status="approvato", test_frequency_value=6, test_frequency_unit="months")
    today = timezone.localdate()
    services.record_test(plan, "superato", user, test_date=today - timedelta(days=10))
    plan.refresh_from_db()
    assert plan.last_test_date == today - timedelta(days=10)
    services.record_test(plan, "superato", user, test_date=today - timedelta(days=100))
    plan.refresh_from_db()
    assert plan.last_test_date == today - timedelta(days=10)


@pytest.mark.django_db
def test_future_test_date_and_archived_plan_rejected(plant, user):
    plan = _plan(plant, user)
    with pytest.raises(ValidationError):
        services.record_test(plan, "superato", user, test_date=timezone.localdate() + timedelta(days=1))
    plan.status = "archiviato"
    plan.save()
    with pytest.raises(ValidationError):
        services.record_test(plan, "superato", user)


@pytest.mark.django_db
def test_delete_test_realigns_dates(plant, user):
    plan = _plan(plant, user, status="approvato")
    today = timezone.localdate()
    services.record_test(plan, "superato", user, test_date=today - timedelta(days=30))
    newest, _w = services.record_test(plan, "superato", user, test_date=today)
    services.delete_test(newest, user)
    plan.refresh_from_db()
    assert plan.last_test_date == today - timedelta(days=30)


@pytest.mark.django_db
def test_rpo_and_rto_warnings_are_structured(plant, user, process):
    plan = _plan(plant, user, process, status="approvato")
    _t, warnings = services.record_test(plan, "superato", user, rto_achieved=30, rpo_achieved=6)
    codes = {w["code"] for w in warnings}
    assert codes == {"rto_over_mtpd", "rto_over_target", "rpo_over_target"}
    assert all(w["process"] == "Stampaggio" for w in warnings)


# ── Copertura ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_coverage_three_states(plant, user):
    from apps.bia.models import CriticalProcess

    today = timezone.localdate()
    ok = CriticalProcess.objects.create(plant=plant, name="OK", criticality=5)
    never = CriticalProcess.objects.create(plant=plant, name="Mai", criticality=5)
    late = CriticalProcess.objects.create(plant=plant, name="Scaduto", criticality=4)
    draft = CriticalProcess.objects.create(plant=plant, name="Bozza", criticality=4)
    _plan(plant, user, ok, status="approvato", last_test_date=today - timedelta(days=5),
          next_test_date=today + timedelta(days=300))
    _plan(plant, user, never, status="approvato")
    _plan(plant, user, late, status="approvato", last_test_date=today - timedelta(days=400),
          next_test_date=today - timedelta(days=35))
    _plan(plant, user, draft, status="bozza", last_test_date=today, next_test_date=today + timedelta(days=30))

    cov = services.process_coverage([ok.pk, never.pk, late.pk, draft.pk])
    assert cov == {ok.pk: "covered", never.pk: "test_expired", late.pk: "test_expired"}

    qs = CriticalProcess.objects.filter(plant=plant)
    assert [p.name for p in services.critical_processes_without_bcp(qs)] == ["Bozza"]
    assert {p.name for p in services.critical_processes_test_expired(qs)} == {"Mai", "Scaduto"}


@pytest.mark.django_db
def test_coverage_endpoint(client, plant, user, process):
    _plan(plant, user, process, status="approvato")
    resp = client.get(f"{URL_PLANS}coverage/?plant={plant.id}")
    assert resp.status_code == 200
    row = resp.data[0]
    assert row["process_name"] == "Stampaggio"
    assert row["coverage"] == "test_expired"
    assert row["plans"][0]["test_state"] == "never"


@pytest.mark.django_db
def test_overdue_task_once_and_plan_stays_approved(plant, user):
    from apps.tasks.models import Task

    today = timezone.localdate()
    plan = _plan(plant, user, status="approvato", last_test_date=today - timedelta(days=400),
                 next_test_date=today - timedelta(days=1))
    assert services.open_overdue_test_tasks() == 1
    assert services.open_overdue_test_tasks() == 0
    plan.refresh_from_db()
    assert plan.status == "approvato"
    assert Task.objects.filter(source_module="M16", source_id=plan.pk).count() == 1


# ── RTO dimostrato ───────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_bia_status_uses_demonstrated_rto(plant, user, process):
    plan = _plan(plant, user, process, status="approvato", rto_hours=4)
    assert process.rto_bcp_status == "ok"          # dichiarato 4h ≤ 8h
    services.record_test(plan, "superato", user, rto_achieved=30)
    assert process.rto_bcp_status == "critical"    # dimostrato 30h


# ── Approvazione ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_ciso_nomination_on_plant_can_approve(plant, user):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    from apps.governance.models import NormativeRole, RoleAssignment

    ciso = User.objects.create_user(username="ciso_p", email="ciso_p@test.com", password="test")
    UserPlantAccess.objects.create(user=ciso, role=GrcRole.RISK_MANAGER, scope_type="org")
    RoleAssignment.objects.create(user=ciso, role=NormativeRole.CISO, scope_type="plant",
                                  scope_id=plant.id, valid_from=timezone.localdate())
    plan = _plan(plant, user)
    other = _plan(_plant("BCO"), user)
    assert services.can_approve_plan(ciso, plan)
    assert not services.can_approve_plan(ciso, other)

    c = APIClient()
    c.force_authenticate(user=ciso)
    assert c.post(f"{URL_PLANS}{other.id}/approve/").status_code == 403
    resp = c.post(f"{URL_PLANS}{plan.id}/approve/")
    assert resp.status_code == 200
    assert resp.data["status"] == "approvato"
    assert c.post(f"{URL_PLANS}{plan.id}/approve/").status_code == 400  # già approvato


@pytest.mark.django_db
def test_archive_removes_coverage(client, plant, user, process):
    plan = _plan(plant, user, process, status="approvato")
    assert client.post(f"{URL_PLANS}{plan.id}/archive/").status_code == 200
    plan.refresh_from_db()
    assert plan.status == "archiviato"
    assert services.process_coverage([process.pk]) == {}


# ── Processi e documento ─────────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_with_processes_and_document(client, plant, process):
    from apps.documents.models import Document

    doc = Document.objects.create(title="BCP Stampaggio", category="procedura", plant=plant)
    resp = client.post(URL_PLANS, {
        "plant": str(plant.id), "title": "Piano", "document": str(doc.id),
        "critical_processes": [str(process.id)],
    }, format="json")
    assert resp.status_code == 201, resp.data
    assert resp.data["critical_processes"] == [str(process.id)]
    assert resp.data["document_title"] == "BCP Stampaggio"
    assert resp.data["test_state"] == "never"


@pytest.mark.django_db
def test_legacy_fk_goes_into_process_list(client, plant, process):
    resp = client.post(URL_PLANS, {
        "plant": str(plant.id), "title": "Wizard", "critical_process": str(process.id),
    }, format="json")
    assert resp.status_code == 201, resp.data
    plan = BcpPlan.objects.get(pk=resp.data["id"])
    assert plan.critical_process_id is None
    assert list(plan.critical_processes.values_list("pk", flat=True)) == [process.pk]


@pytest.mark.django_db
def test_process_or_document_of_other_plant_rejected(client, plant):
    from apps.bia.models import CriticalProcess
    from apps.documents.models import Document

    other = _plant("BCX")
    foreign_proc = CriticalProcess.objects.create(plant=other, name="Altro", criticality=4)
    resp = client.post(URL_PLANS, {
        "plant": str(plant.id), "title": "P", "critical_processes": [str(foreign_proc.id)],
    }, format="json")
    assert resp.status_code == 400
    assert not BcpPlan.objects.filter(title="P").exists()

    foreign_doc = Document.objects.create(title="Doc altro sito", category="procedura", plant=other)
    resp = client.post(URL_PLANS, {
        "plant": str(plant.id), "title": "P2", "document": str(foreign_doc.id),
    }, format="json")
    assert resp.status_code == 400
    org_doc = Document.objects.create(title="Doc org", category="procedura", plant=None)
    resp = client.post(URL_PLANS, {
        "plant": str(plant.id), "title": "P3", "document": str(org_doc.id),
    }, format="json")
    assert resp.status_code == 201


@pytest.mark.django_db
def test_tests_endpoint_date_and_no_edit(client, plant, user):
    plan = _plan(plant, user, status="approvato")
    past = timezone.localdate() - timedelta(days=7)
    resp = client.post(URL_TESTS, {"plan": str(plan.id), "result": "superato",
                                   "test_date": past.isoformat()}, format="json")
    assert resp.status_code == 201
    test_id = resp.data["test"]["id"]
    assert resp.data["test"]["test_date"] == past.isoformat()
    assert client.patch(f"{URL_TESTS}{test_id}/", {"result": "fallito"}, format="json").status_code == 405
    listed = client.get(f"{URL_TESTS}?plan__plant={plant.id}")
    assert listed.status_code == 200


@pytest.mark.django_db
def test_test_on_plan_outside_scope_not_found(plant, user):
    from apps.auth_grc.models import GrcRole, UserPlantAccess

    other = _plant("BCZ")
    plan = _plan(other, user)
    local = User.objects.create_user(username="rm_local", email="rm_local@test.com", password="test")
    acc = UserPlantAccess.objects.create(user=local, role=GrcRole.RISK_MANAGER, scope_type="single_plant")
    acc.scope_plants.add(plant)
    c = APIClient()
    c.force_authenticate(user=local)
    resp = c.post(URL_TESTS, {"plan": str(plan.id), "result": "superato"}, format="json")
    assert resp.status_code in (403, 404)
    assert not plan.tests.exists()


# ── Evidenze del test ────────────────────────────────────────────────────────

def _pdf(name="report.pdf"):
    from django.core.files.uploadedfile import SimpleUploadedFile

    return SimpleUploadedFile(name, b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n", content_type="application/pdf")


@pytest.mark.django_db
def test_record_test_with_existing_evidence_of_site_or_org(plant, user):
    from apps.documents.models import Evidence

    plan = _plan(plant, user, status="approvato")
    ev_site = Evidence.objects.create(title="Log restore", plant=plant, created_by=user)
    ev_org = Evidence.objects.create(title="Report DR org", plant=None, created_by=user)
    test, _w = services.record_test(plan, "superato", user, evidence_ids=[str(ev_site.pk), str(ev_org.pk)])
    assert set(test.evidences.values_list("pk", flat=True)) == {ev_site.pk, ev_org.pk}


@pytest.mark.django_db
def test_evidence_of_other_site_blocks_the_test(plant, user):
    from apps.documents.models import Evidence

    plan = _plan(plant, user, status="approvato")
    foreign = Evidence.objects.create(title="Altro sito", plant=_plant("BCE"), created_by=user)
    with pytest.raises(ValidationError):
        services.record_test(plan, "superato", user, evidence_ids=[str(foreign.pk)])
    assert not plan.tests.exists()


@pytest.mark.django_db
def test_invalid_file_blocks_the_test_instead_of_being_lost(plant, user):
    from django.core.files.uploadedfile import SimpleUploadedFile

    plan = _plan(plant, user, status="approvato")
    bad = SimpleUploadedFile("script.exe", b"MZ\x90\x00", content_type="application/octet-stream")
    with pytest.raises(ValidationError):
        services.record_test(plan, "superato", user, evidence_file=bad)
    assert not plan.tests.exists()


@pytest.mark.django_db
def test_add_evidences_to_existing_test(client, plant, user, settings, tmp_path):
    from apps.documents.models import Evidence

    settings.MEDIA_ROOT = str(tmp_path)
    plan = _plan(plant, user, status="approvato")
    test, _w = services.record_test(plan, "superato", user)
    ev = Evidence.objects.create(title="Verbale esercitazione", plant=plant, created_by=user)

    resp = client.post(f"{URL_TESTS}{test.id}/evidences/", {"evidence_ids": [str(ev.pk)]}, format="json")
    assert resp.status_code == 200, resp.data
    assert resp.data["evidences_count"] == 1
    assert resp.data["evidence_items"][0]["title"] == "Verbale esercitazione"

    resp = client.post(f"{URL_TESTS}{test.id}/evidences/", {"evidence_file": _pdf()}, format="multipart")
    assert resp.status_code == 200, resp.data
    assert resp.data["evidences_count"] == 2
    created = Evidence.objects.exclude(pk=ev.pk).get()
    assert created.evidence_type == "test_result"
    assert created.plant_id == plant.pk

    assert client.post(f"{URL_TESTS}{test.id}/evidences/", {}, format="json").status_code == 400

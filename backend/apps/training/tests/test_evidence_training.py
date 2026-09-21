"""Formazione a evidenze: gruppi, piano, erogazioni con file, permessi, migrazione."""
import base64
from datetime import date, timedelta

import pytest
from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from apps.auth_grc.models import GrcRole, UserPlantAccess

User = get_user_model()

URL_AUD = "/api/v1/training/audiences/"
URL_PLANS = "/api/v1/training/plans/"
URL_ITEMS = "/api/v1/training/plan-items/"
URL_SESS = "/api/v1/training/sessions/"

_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNk"
    "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def _proof():
    return SimpleUploadedFile("registro.png", _PNG, content_type="image/png")


@pytest.fixture(autouse=True)
def _media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _user(name, role=None, scope="org", plants=()):
    u = User.objects.create_user(username=name, email=f"{name}@t.it", password="x")
    if role:
        a = UserPlantAccess.objects.create(user=u, role=role, scope_type=scope)
        if plants:
            a.scope_plants.set(plants)
    return u


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="TA", name="Plant A", country="IT",
                                nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def plant_b(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="TB", name="Plant B", country="IT",
                                nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def co(db):
    return _user("co", GrcRole.COMPLIANCE_OFFICER)


@pytest.fixture
def course(db, co):
    from apps.training.models import TrainingCourse
    return TrainingCourse.objects.create(
        title="Awareness base", kind="corso", mandatory=True, validity_months=12, created_by=co,
    )


@pytest.fixture
def phishing_course(db, co):
    from apps.training.models import TrainingCourse
    return TrainingCourse.objects.create(title="Phishing Q1", kind="phishing", created_by=co)


@pytest.fixture
def audiences(plant):
    from apps.training.models import TrainingAudience
    today = timezone.localdate()
    return [
        TrainingAudience.objects.create(plant=plant, name="Produzione", headcount=200,
                                        headcount_updated_at=today),
        TrainingAudience.objects.create(plant=plant, name="Uffici", headcount=40,
                                        headcount_updated_at=today),
    ]


def _session_payload(course, plant, **extra):
    data = {
        "course": str(course.pk),
        "plant": str(plant.pk),
        "held_on": (timezone.localdate() - timedelta(days=3)).isoformat(),
        "file": _proof(),
    }
    data.update(extra)
    return data


# ── Gruppi di destinatari ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_audience_headcount_date_tracks_changes(co, plant):
    from apps.training.models import TrainingAudience
    c = _client(co)
    r = c.post(URL_AUD, {"plant": str(plant.pk), "name": "IT/OT", "headcount": 12}, format="json")
    assert r.status_code == 201, r.data
    aud = TrainingAudience.objects.get(pk=r.data["id"])
    aud.headcount_updated_at = date(2025, 1, 1)
    aud.save()
    r = c.patch(f"{URL_AUD}{aud.pk}/", {"notes": "solo nota"}, format="json")
    aud.refresh_from_db()
    assert aud.headcount_updated_at == date(2025, 1, 1)
    c.patch(f"{URL_AUD}{aud.pk}/", {"headcount": 15}, format="json")
    aud.refresh_from_db()
    assert aud.headcount == 15 and aud.headcount_updated_at == timezone.localdate()


@pytest.mark.django_db
def test_plant_manager_cannot_manage_other_site(plant, plant_b):
    pm = _user("pm", GrcRole.PLANT_MANAGER, scope="single_plant", plants=[plant_b])
    r = _client(pm).post(URL_AUD, {"plant": str(plant.pk), "name": "X", "headcount": 1},
                         format="json")
    assert r.status_code == 403


# ── Erogazioni ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_register_session_creates_evidence(co, course, plant, audiences):
    from apps.training.models import TrainingSession
    held = timezone.localdate() - timedelta(days=3)
    r = _client(co).post(URL_SESS, _session_payload(
        course, plant, audiences=[str(a.pk) for a in audiences], trained_count=230,
    ), format="multipart")
    assert r.status_code == 201, r.data
    s = TrainingSession.objects.select_related("evidence").get(pk=r.data["id"])
    assert s.target_count == 240  # somma dei gruppi
    ev = s.evidence
    assert ev.evidence_type == "certificato"
    assert ev.plant_id == plant.pk
    assert ev.file_path
    assert ev.valid_until == held + relativedelta(months=12)


@pytest.mark.django_db
def test_register_session_requires_file(co, course, plant):
    data = _session_payload(course, plant, target_count=10, trained_count=5)
    data.pop("file")
    r = _client(co).post(URL_SESS, data, format="multipart")
    assert r.status_code == 400 and "file" in r.data


@pytest.mark.django_db
@pytest.mark.parametrize("extra,field", [
    ({"target_count": 10, "trained_count": 11}, "trained_count"),
    ({"trained_count": 5}, "target_count"),
    ({"target_count": 10, "trained_count": 5,
      "held_on": (date.today() + timedelta(days=5)).isoformat()}, "held_on"),
])
def test_register_session_validation(co, course, plant, extra, field):
    r = _client(co).post(URL_SESS, _session_payload(course, plant, **extra), format="multipart")
    assert r.status_code == 400 and field in r.data


@pytest.mark.django_db
def test_register_session_rejects_audience_of_other_site(co, course, plant_b, audiences):
    r = _client(co).post(URL_SESS, _session_payload(
        course, plant_b, audiences=[str(audiences[0].pk)], trained_count=1,
    ), format="multipart")
    assert r.status_code == 400 and "audiences" in r.data


@pytest.mark.django_db
def test_phishing_counts(co, phishing_course, plant):
    c = _client(co)
    bad = c.post(URL_SESS, _session_payload(
        phishing_course, plant, sent_count=100, clicked_count=70, reported_count=40,
    ), format="multipart")
    assert bad.status_code == 400
    ok = c.post(URL_SESS, _session_payload(
        phishing_course, plant, sent_count=100, clicked_count=12, reported_count=30,
    ), format="multipart")
    assert ok.status_code == 201, ok.data


@pytest.mark.django_db
def test_update_cannot_replace_file_or_course(co, course, plant):
    from apps.training.models import TrainingCourse
    c = _client(co)
    r = c.post(URL_SESS, _session_payload(course, plant, target_count=10, trained_count=5),
               format="multipart")
    sid = r.data["id"]
    other = TrainingCourse.objects.create(title="Altro", created_by=co)
    assert c.patch(f"{URL_SESS}{sid}/", {"course": str(other.pk)}, format="json").status_code == 400
    assert c.patch(f"{URL_SESS}{sid}/", {"file": _proof()}, format="multipart").status_code == 400
    ok = c.patch(f"{URL_SESS}{sid}/", {"trained_count": 8}, format="json")
    assert ok.status_code == 200 and ok.data["trained_count"] == 8


@pytest.mark.django_db
def test_delete_session_soft_deletes_evidence(co, course, plant):
    from apps.documents.models import Evidence
    from apps.training.models import TrainingSession
    c = _client(co)
    r = c.post(URL_SESS, _session_payload(course, plant, target_count=10, trained_count=5),
               format="multipart")
    s = TrainingSession.objects.get(pk=r.data["id"])
    assert c.delete(f"{URL_SESS}{s.pk}/").status_code == 204
    assert not TrainingSession.objects.filter(pk=s.pk).exists()
    assert Evidence.objects.all_with_deleted().get(pk=s.evidence_id).deleted_at is not None


# ── Piano ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_plan_status_and_auto_match(co, course, plant, audiences):
    from apps.training.models import TrainingPlan, TrainingPlanItem, TrainingSession
    today = timezone.localdate()
    plan = TrainingPlan.objects.create(plant=plant, year=today.year, created_by=co)
    item = TrainingPlanItem.objects.create(plan=plan, course=course, due_date=today + timedelta(days=10))
    item.audiences.set(audiences)
    c = _client(co)
    st = c.get(f"{URL_PLANS}{plan.pk}/status/").data
    assert st["items"][0]["state"] == "in_scadenza"

    r = c.post(URL_SESS, _session_payload(
        course, plant, held_on=today.isoformat(), audiences=[str(a.pk) for a in audiences],
        trained_count=180,
    ), format="multipart")
    assert r.status_code == 201, r.data
    assert TrainingSession.objects.get(pk=r.data["id"]).plan_item_id == item.pk

    st = c.get(f"{URL_PLANS}{plan.pk}/status/").data
    row = st["items"][0]
    assert row["state"] == "fatto" and row["target_count"] == 240 and row["coverage_pct"] == 75.0
    # Piano con erogazioni: non si elimina.
    assert c.delete(f"{URL_PLANS}{plan.pk}/").status_code == 400


@pytest.mark.django_db
def test_org_plan_needs_org_scope(plant):
    pm = _user("pm2", GrcRole.PLANT_MANAGER, scope="single_plant", plants=[plant])
    r = _client(pm).post(URL_PLANS, {"year": 2026}, format="json")
    assert r.status_code == 403


@pytest.mark.django_db
def test_plan_item_audiences_same_site(co, course, plant, plant_b, audiences):
    from apps.training.models import TrainingPlan
    plan = TrainingPlan.objects.create(plant=plant_b, year=2026, created_by=co)
    r = _client(co).post(URL_ITEMS, {
        "plan": str(plan.pk), "course": str(course.pk), "due_date": "2026-12-31",
        "audiences": [str(audiences[0].pk)],
    }, format="json")
    assert r.status_code == 400 and "audiences" in r.data


# ── Permessi ────────────────────────────────────────────────────────────────

def _ciso(user, scope_type, scope_id=None):
    from apps.governance.models import RoleAssignment
    RoleAssignment.objects.create(user=user, role="ciso", scope_type=scope_type,
                                  scope_id=scope_id, valid_from=date(2025, 1, 1))


@pytest.mark.django_db
def test_ciso_registers_only_on_own_site(course, plant, plant_b):
    ciso = _user("ciso", GrcRole.INTERNAL_AUDITOR)  # accesso GRC in sola lettura
    _ciso(ciso, "plant", plant.pk)
    c = _client(ciso)
    ok = c.post(URL_SESS, _session_payload(course, plant, target_count=5, trained_count=5),
                format="multipart")
    assert ok.status_code == 201, ok.data
    ko = c.post(URL_SESS, _session_payload(course, plant_b, target_count=5, trained_count=5),
                format="multipart")
    assert ko.status_code == 403


@pytest.mark.django_db
def test_expired_ciso_cannot_write(course, plant):
    from apps.governance.models import RoleAssignment
    ciso = _user("ex_ciso", GrcRole.INTERNAL_AUDITOR)
    RoleAssignment.objects.create(user=ciso, role="ciso", scope_type="org",
                                  valid_from=date(2024, 1, 1), valid_until=date(2024, 12, 31))
    r = _client(ciso).post(URL_SESS, _session_payload(course, plant, target_count=5,
                                                      trained_count=5), format="multipart")
    assert r.status_code == 403


@pytest.mark.django_db
def test_auditors_read_but_do_not_write(course, plant):
    for role in (GrcRole.EXTERNAL_AUDITOR, GrcRole.INTERNAL_AUDITOR):
        c = _client(_user(f"a_{role}", role))
        assert c.get(URL_SESS).status_code == 200
        assert c.get(URL_AUD).status_code == 200
        r = c.post(URL_SESS, _session_payload(course, plant, target_count=5, trained_count=5),
                   format="multipart")
        assert r.status_code == 403


@pytest.mark.django_db
def test_operational_role_cannot_read_records():
    c = _client(_user("rm", GrcRole.RISK_MANAGER))
    assert c.get(URL_SESS).status_code == 403


# ── Migrazione dati storici ─────────────────────────────────────────────────

@pytest.mark.django_db
def test_legacy_migration_aggregates_and_is_idempotent(co, plant):
    from apps.controls.models import Control, ControlDomain, Framework
    from apps.plants.models import Plant
    from apps.training.legacy import (
        LEGACY_PHISHING_TITLE,
        apply_legacy_migration,
        plan_legacy_migration,
    )
    from apps.training.models import (
        PhishingSimulation,
        TrainingCourse,
        TrainingEnrollment,
        TrainingSession,
    )

    fw = Framework.objects.create(code="ISO-T", name="ISO", version="1",
                                  published_at=timezone.localdate())
    dom = ControlDomain.objects.create(framework=fw, code="A6", translations={"it": {"name": "A6"}},
                                       order=1)
    ctrl = Control.objects.create(framework=fw, domain=dom, external_id="A.6.3",
                                  translations={"it": {"name": "N"}}, level="L2",
                                  evidence_requirement={}, control_category="organizzativo")
    course = TrainingCourse.objects.create(title="Storico", framework_refs=["A.6.3", "X.9"],
                                           created_by=co)
    course.plants.add(plant)
    users = [_user(f"e{i}") for i in range(3)]
    now = timezone.now()
    TrainingEnrollment.objects.create(course=course, user=users[0], status="completato",
                                      completed_at=now)
    TrainingEnrollment.objects.create(course=course, user=users[1], status="completato",
                                      completed_at=now - timedelta(days=20))
    TrainingEnrollment.objects.create(course=course, user=users[2], status="assegnato")
    for u, res in zip(users, ["clicked", "reported", "ignored"], strict=True):
        PhishingSimulation.objects.create(kb4_simulation_id="C1", user=u, plant=plant,
                                          result=res, sent_at=now)

    args = (TrainingCourse, TrainingEnrollment, PhishingSimulation, Control, Plant)
    plan = plan_legacy_migration(*args)
    assert plan["unmatched_refs"] == [{"course": "Storico", "ref": "X.9"}]
    apply_legacy_migration(plan, TrainingCourse, TrainingSession)
    apply_legacy_migration(plan_legacy_migration(*args), TrainingCourse, TrainingSession)

    assert list(course.controls.all()) == [ctrl]
    s = TrainingSession.objects.get(course=course)
    assert (s.legacy, s.plant_id, s.target_count, s.trained_count) == (True, plant.pk, 3, 2)
    assert s.held_on == timezone.localdate()
    ph = TrainingSession.objects.get(course__title=LEGACY_PHISHING_TITLE)
    assert (ph.sent_count, ph.clicked_count, ph.reported_count) == (3, 1, 1)
    assert ph.course.kind == "phishing" and ph.course.source == "kb4"
    assert TrainingSession.objects.count() == 2  # la seconda esecuzione non duplica
    # I dati per persona restano intatti.
    assert TrainingEnrollment.objects.count() == 3 and PhishingSimulation.objects.count() == 3

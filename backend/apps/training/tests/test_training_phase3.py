"""Formazione a evidenze, fase 3: indicatori (KPI, Reporting, Cockpit) e pacchetto audit."""
import csv
from datetime import date, timedelta

import pytest
from django.utils import timezone

TODAY = date(2026, 9, 21)


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


def _course(**kw):
    from apps.training.models import TrainingCourse
    kw.setdefault("title", "Awareness")
    kw.setdefault("mandatory", True)
    kw.setdefault("validity_months", 12)
    return TrainingCourse.objects.create(**kw)


def _aud(plant, name, headcount, updated=TODAY):
    from apps.training.models import TrainingAudience
    return TrainingAudience.objects.create(plant=plant, name=name, headcount=headcount,
                                           headcount_updated_at=updated)


def _item(course, plant, due, audiences=(), year=None):
    from apps.training.models import TrainingPlan, TrainingPlanItem
    plan, _ = TrainingPlan.objects.get_or_create(plant=plant, year=year or due.year)
    item = TrainingPlanItem.objects.create(plan=plan, course=course, due_date=due)
    item.audiences.set(audiences)
    return item


def _session(course, plant, held_on, **kw):
    from apps.training.models import TrainingSession
    return TrainingSession.objects.create(course=course, plant=plant, held_on=held_on, **kw)


# ── Copertura ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_coverage_per_course_and_site(plant, plant_b):
    from apps.training.services import training_coverage

    course = _course()
    prod, uff = _aud(plant, "Produzione", 200), _aud(plant, "Uffici", 50)
    other = _aud(plant_b, "Produzione", 100)
    _item(course, plant, TODAY + timedelta(days=30), [prod, uff])
    # Il piano di organizzazione vale per ogni sito: stesso gruppo non contato due volte.
    _item(course, None, TODAY + timedelta(days=60), [prod, other])

    _session(course, plant, TODAY - timedelta(days=10), target_count=200, trained_count=180)
    _session(course, plant, TODAY - timedelta(days=5), target_count=50, trained_count=90)
    # Scaduta (validità 12 mesi) e storica: non contano.
    _session(course, plant, TODAY - timedelta(days=400), target_count=10, trained_count=10)
    _session(course, plant, TODAY - timedelta(days=20), trained_count=40, legacy=True)
    _session(course, plant_b, TODAY - timedelta(days=3), target_count=100, trained_count=60)

    cov = training_coverage(plant, TODAY)
    assert (cov["target"], cov["covered"]) == (250, 250)  # 270 formati, tetto 250
    assert cov["pct"] == 100.0
    assert [r["plant_code"] for r in cov["rows"]] == ["TA"]

    all_sites = training_coverage(None, TODAY)
    assert (all_sites["target"], all_sites["covered"]) == (350, 310)
    assert all_sites["rows"][0]["plant_code"] == "TB"  # la peggiore in testa
    assert all_sites["rows"][0]["pct"] == 60.0


@pytest.mark.django_db
def test_coverage_ignores_non_general_and_phishing_courses(plant):
    from apps.training.services import training_coverage

    aud = _aud(plant, "IT", 10)
    for course in (_course(title="CdA", audience_kind="organo_gestione"),
                   _course(title="Phish", kind="phishing"),
                   _course(title="Facoltativo", mandatory=False)):
        _item(course, plant, TODAY, [aud])
    # Voce senza gruppi: nessun denominatore.
    _item(_course(title="Senza gruppi"), plant, TODAY)
    # Piano dell'anno scorso: fuori.
    _item(_course(title="Vecchio"), plant, TODAY - timedelta(days=365), [aud])

    cov = training_coverage(plant, TODAY)
    assert cov == {"year": 2026, "target": 0, "covered": 0, "pct": None, "rows": []}


# ── Piano ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_plan_progress(plant):
    from apps.training.services import plan_progress

    course = _course()
    done = _item(course, plant, TODAY - timedelta(days=30))
    _session(course, plant, TODAY - timedelta(days=40), plan_item=done, trained_count=1,
             target_count=1)
    _item(course, plant, TODAY - timedelta(days=1))                    # in ritardo
    _item(course, plant, TODAY + timedelta(days=10))                   # in scadenza
    _item(course, plant, TODAY + timedelta(days=90))                   # pianificata
    _item(course, plant, date(2025, 11, 1))                            # ritardo anno scorso
    _item(_course(title="Archiviato", status="archiviato"), plant, TODAY - timedelta(days=3))

    prog = plan_progress(plant, TODAY)
    assert prog == {"year": 2026, "items": 4, "due": 2, "done": 1, "pct": 50.0,
                    "overdue": 2, "due_soon": 1}


# ── Phishing ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_latest_phishing_per_site(plant, plant_b):
    from apps.training.services import latest_phishing

    phish = _course(title="Phishing", kind="phishing", mandatory=False)
    _session(phish, plant, TODAY - timedelta(days=100), sent_count=100, clicked_count=30)
    _session(phish, plant, TODAY - timedelta(days=10), sent_count=100, clicked_count=5,
             reported_count=40)
    _session(phish, plant_b, TODAY - timedelta(days=20), sent_count=50, clicked_count=5,
             reported_count=10, legacy=True)
    _session(phish, plant_b, TODAY - timedelta(days=500), sent_count=50, clicked_count=50)

    ph = latest_phishing(None, TODAY)
    assert (ph["sent"], ph["clicked"], ph["reported"]) == (150, 10, 50)
    assert ph["click_pct"] == 6.7 and ph["report_pct"] == 33.3
    assert [c["plant_code"] for c in ph["campaigns"]] == ["TA", "TB"]
    assert latest_phishing(plant_b, TODAY)["campaigns"][0]["legacy"] is True


# ── Prove in scadenza e headcount da riverificare ───────────────────────────

@pytest.mark.django_db
def test_expiring_evidence_only_latest_per_course_and_site(plant):
    from apps.documents.models import Evidence
    from apps.training.services import expiring_training_evidence

    course = _course()

    def with_evidence(held_on, valid_until):
        ev = Evidence.objects.create(title="x", evidence_type="certificato", plant=plant,
                                     valid_until=valid_until)
        return _session(course, plant, held_on, evidence=ev, trained_count=1, target_count=1)

    with_evidence(TODAY - timedelta(days=700), TODAY - timedelta(days=335))  # sostituita
    latest = with_evidence(TODAY - timedelta(days=340), TODAY + timedelta(days=25))
    other = _course(title="Altro")
    ev = Evidence.objects.create(title="y", evidence_type="certificato", plant=plant,
                                 valid_until=TODAY - timedelta(days=2))
    expired = _session(other, plant, TODAY - timedelta(days=367), evidence=ev)

    rows = expiring_training_evidence(plant, TODAY)
    assert [(r["session_id"], r["expired"]) for r in rows] == [
        (str(expired.pk), True), (str(latest.pk), False),
    ]


@pytest.mark.django_db
def test_stale_audiences(plant):
    from apps.training.services import stale_audiences_count

    _aud(plant, "Vecchio", 10, updated=TODAY - timedelta(days=200))
    _aud(plant, "Fresco", 10, updated=TODAY - timedelta(days=30))
    assert stale_audiences_count(plant, TODAY) == 1


# ── Reporting ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_reporting_training_section_has_no_personal_data(plant):
    from django.contrib.auth import get_user_model

    from apps.reporting.services import kpi_overview
    from apps.training.models import TrainingEnrollment

    course = _course()
    today = timezone.localdate()
    _item(course, plant, today, [_aud(plant, "Produzione", 20)])
    _session(course, plant, today - timedelta(days=1), target_count=20, trained_count=15)
    u = get_user_model().objects.create_user(username="x", email="persona@t.it", password="x")
    TrainingEnrollment.objects.create(course=course, user=u, status="completato")

    tr = kpi_overview(str(plant.pk))["training"]
    assert set(tr) == {"coverage", "plan", "phishing", "expiring_evidence", "stale_audiences", "board"}
    assert tr["coverage"]["pct"] == 75.0
    assert "persona@t.it" not in repr(tr)


# ── Pacchetto audit ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_audit_pack_training_is_site_scoped_and_anonymous(plant, plant_b, tmp_path):
    from django.contrib.auth import get_user_model

    from apps.audit_prep.audit_pack import _collect_training
    from apps.training.models import TrainingEnrollment

    course = _course()
    today = timezone.localdate()
    _item(course, plant, today, [_aud(plant, "Produzione", 20)])
    _item(course, None, today + timedelta(days=20))
    _session(course, plant, today - timedelta(days=1), target_count=20, trained_count=15)
    _session(course, plant_b, today - timedelta(days=1), target_count=5, trained_count=5)
    u = get_user_model().objects.create_user(username="x", email="persona@t.it", password="x")
    TrainingEnrollment.objects.create(course=course, user=u, status="completato")

    out = _collect_training(tmp_path, plant)
    assert out == {"plan_items": 2, "sessions": 1, "coverage_pct": 75.0,
                   "board_training_pct": None}

    folder = tmp_path / "07_training"
    assert sorted(p.name for p in folder.iterdir()) == [
        "audiences.csv", "board_training.csv", "coverage.csv", "plan_items.csv", "sessions.csv",
    ]
    with (folder / "plan_items.csv").open(encoding="utf-8") as fp:
        scopes = sorted(r["plan_scope"] for r in csv.DictReader(fp))
    assert scopes == ["organizzazione", "sito"]
    assert not any("persona@t.it" in p.read_text(encoding="utf-8") for p in folder.iterdir())

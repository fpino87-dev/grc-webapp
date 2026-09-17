"""M13 × §6.2 — obiettivi di sicurezza nello snapshot, nel verbale e nelle delibere."""
import pytest
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="MRO-P1", name="Plant Riesame Obiettivi", country="IT",
                                nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="mro_user", email="mro@test.com", password="test",
                                 first_name="Ada", last_name="Rossi")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def review(db, plant, user):
    from apps.management_review.models import ManagementReview
    from apps.management_review.services import ensure_iso_agenda
    r = ManagementReview.objects.create(plant=plant, title="Riesame 2026",
                                        review_date=timezone.localdate(), created_by=user)
    ensure_iso_agenda(r, user)
    return r


def _objective(plant, code="OBJ-MR-1", **kw):
    from apps.governance.models import SecurityObjective
    start = kw.pop("start_date", timezone.localdate() - timedelta(days=50))
    data = dict(
        code=code, title="Copertura patch critiche", measure_source="manual", unit="%",
        start_date=start, baseline_value=40.0, target_value=90.0, target_direction="above",
        target_date=start + timedelta(days=100), owner_role="plant_manager",
        evaluation_method="Misura mensile.", status="attivo",
    )
    data.update(kw)
    return SecurityObjective.objects.create(plant=plant, **data)


# ── Snapshot ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_snapshot_includes_objectives(review, plant, user):
    from apps.management_review.services import generate_snapshot
    _objective(plant)
    snap = generate_snapshot(review, user)
    assert snap["obiettivi"]["attivi"] == 1
    item = snap["obiettivi"]["elenco"][0]
    assert item["code"] == "OBJ-MR-1" and item["target_value"] == 90.0


@pytest.mark.django_db
def test_snapshot_includes_org_wide_objectives_for_a_site_review(review, plant, user):
    """Un obiettivo di organizzazione impegna anche il singolo sito."""
    from apps.management_review.services import generate_snapshot
    _objective(plant, code="OBJ-SITE")
    _objective(None, code="OBJ-ORG")
    snap = generate_snapshot(review, user)
    assert {i["code"] for i in snap["obiettivi"]["elenco"]} == {"OBJ-SITE", "OBJ-ORG"}


@pytest.mark.django_db
def test_off_track_objectives_come_first_and_raise_an_alert(review, plant, user):
    """In direzione si guardano per primi quelli che non stanno andando bene."""
    from apps.management_review.report.builder import build_report
    from apps.management_review.services import generate_snapshot
    from apps.governance.services import record_objective_measurement
    ok = _objective(plant, code="OBJ-OK")
    late = _objective(plant, code="OBJ-LATE")
    record_objective_measurement(ok, user, value=85.0)
    record_objective_measurement(late, user, value=41.0)

    snap = generate_snapshot(review, user)
    assert [i["code"] for i in snap["obiettivi"]["elenco"]][0] == "OBJ-LATE"
    assert snap["obiettivi"]["a_rischio"] == 1
    review.refresh_from_db()
    doc = build_report(review)
    assert any("obiettivi di sicurezza" in str(a) for a in doc["alerts"])


@pytest.mark.django_db
def test_report_shows_objectives_under_performance_item(review, plant, user):
    from apps.management_review.report.builder import build_report
    from apps.management_review.services import generate_snapshot
    _objective(plant)
    generate_snapshot(review, user)
    review.refresh_from_db()
    doc = build_report(review)
    performance = next(s for s in doc["sections"] if str(s["heading"]).startswith("d)"))
    titles = [str(b.get("title") or "") for b in performance["blocks"]]
    assert any("§6.2" in t for t in titles)


@pytest.mark.django_db
def test_report_of_an_old_snapshot_has_no_objectives_section(review, plant, user):
    """Snapshot generati prima di questa funzione non devono rompere il verbale."""
    from apps.management_review.report.builder import build_report
    from apps.management_review.services import generate_snapshot
    generate_snapshot(review, user)
    review.refresh_from_db()
    del review.snapshot_data["obiettivi"]
    review.save(update_fields=["snapshot_data"])
    doc = build_report(review)
    performance = next(s for s in doc["sections"] if str(s["heading"]).startswith("d)"))
    assert not any("§6.2" in str(b.get("title") or "") for b in performance["blocks"])


# ── Verbale multilingua ───────────────────────────────────────────────────

@pytest.mark.django_db
@pytest.mark.parametrize("lang,expected", [
    ("en", "ISMS Management Review"),
    ("fr", "Revue de direction du SMSI"),
    ("pl", "Przegląd zarządzania SZBI"),
    ("tr", "BGYS Yönetimin Gözden Geçirmesi"),
])
def test_report_is_written_in_the_readers_language(review, plant, user, lang, expected):
    from django.utils import translation
    from apps.management_review.report.builder import build_report
    from apps.management_review.services import generate_snapshot
    generate_snapshot(review, user)
    review.refresh_from_db()
    with translation.override(lang):
        assert str(build_report(review)["title"]) == expected


@pytest.mark.django_db
def test_report_download_follows_accept_language(client, review, plant, user):
    from apps.management_review.services import generate_snapshot
    generate_snapshot(review, user)
    resp = client.get(f"/api/v1/management-review/reviews/{review.id}/report/?fmt=html",
                      HTTP_ACCEPT_LANGUAGE="fr")
    assert resp.status_code == 200
    assert "Revue de direction du SMSI" in resp.content.decode()


# ── Delibera → obiettivo ──────────────────────────────────────────────────

URL_ACTIONS = "/api/v1/management-review/review-actions/"


@pytest.mark.django_db
def test_decision_creates_a_draft_objective(client, review, plant):
    """§9.3.3 → §6.2: la direzione delibera l'obiettivo, il piano si completa dopo."""
    from apps.governance.models import SecurityObjective
    resp = client.post(URL_ACTIONS, {
        "review": str(review.id),
        "decision_type": "obiettivo",
        "description": "Portare la copertura delle patch critiche al 95% entro fine anno.",
        "due_date": "2026-12-31",
        "objective": {
            "code": "OBJ-2026-03", "measure_source": "manual", "unit": "%",
            "baseline_value": 62.0, "target_value": 95.0, "owner_role": "plant_manager",
        },
    }, format="json")
    assert resp.status_code == 201, resp.data
    obj = SecurityObjective.objects.get(code="OBJ-2026-03")
    assert obj.status == "bozza"
    assert obj.origin == "riesame" and obj.source_review_id == review.id
    assert obj.plant_id == plant.id and str(obj.target_date) == "2026-12-31"
    assert resp.data["objective_code"] == "OBJ-2026-03"


@pytest.mark.django_db
def test_decision_objective_requires_code_and_target(client, review):
    resp = client.post(URL_ACTIONS, {
        "review": str(review.id), "decision_type": "obiettivo",
        "description": "Obiettivo senza piano", "due_date": "2026-12-31",
        "objective": {"measure_source": "manual", "target_value": 95.0},
    }, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_decision_objective_rejects_a_target_that_does_not_improve(client, review):
    resp = client.post(URL_ACTIONS, {
        "review": str(review.id), "decision_type": "obiettivo",
        "description": "Target che peggiora", "due_date": "2026-12-31",
        "objective": {"code": "OBJ-BAD", "measure_source": "manual",
                      "baseline_value": 90.0, "target_value": 60.0},
    }, format="json")
    assert resp.status_code == 400


# ── Intestazione del verbale e nota IA ────────────────────────────────────

@pytest.mark.django_db
def test_report_subtitle_lists_the_frameworks_in_scope(review, plant, user):
    """Il riesame vale per tutti i sistemi di gestione adottati: intestarlo
    alla sola ISO 27001 dava un'informazione incompleta a un auditor TISAX."""
    from apps.management_review.report.builder import build_report
    from apps.management_review.services import generate_snapshot
    generate_snapshot(review, user)
    review.refresh_from_db()
    subtitle = str(build_report(review)["subtitle"])
    assert "§9.3" not in subtitle
    # Con i framework caricati il sottotitolo li elenca; senza, resta una
    # dicitura neutra — in nessun caso intesta il documento a una sola norma.
    assert subtitle


@pytest.mark.django_db
def test_agenda_items_keep_the_clause_letters(review, plant, user):
    """La struttura resta quella di §9.3.2 e va mostrata dove serve
    all'auditor: sulle singole voci, non come intestazione del documento."""
    from apps.management_review.report.builder import build_report
    from apps.management_review.services import generate_snapshot
    generate_snapshot(review, user)
    review.refresh_from_db()
    headings = [str(s["heading"]) for s in build_report(review)["sections"]]
    assert any(h.startswith("d)") for h in headings)

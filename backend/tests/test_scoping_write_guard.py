"""Sweep security 2026-06-12 fase 2 — residui chiusi.

1. Guard sulle SCRITTURE (require_payload_plant_access via mixin): un utente
   plant-scoped non può creare/spostare oggetti su un plant fuori perimetro
   passando l'id nel body (FK diretto, M2M di Plant, FK a oggetto correlato).
2. Directory siti/BU scoped: un plant_manager vede e modifica solo i propri
   siti (prima poteva fare PATCH su QUALSIASI sito).
3. Training scoped: corsi/iscrizioni di altri siti invisibili; corsi globali
   (senza plants) visibili a tutti; completion-rate via queryset scoped.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.auth_grc.models import GrcRole, UserPlantAccess
from apps.plants.models import Plant

User = get_user_model()


def _make_user(username, role, scope_type="org", plants=()):
    u = User.objects.create_user(username=username, email=f"{username}@test.com", password="x")
    access = UserPlantAccess.objects.create(user=u, role=role, scope_type=scope_type)
    for p in plants:
        access.scope_plants.add(p)
    return u


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def plant_a(db):
    return Plant.objects.create(code="WG-A", name="Plant A", country="IT",
                                nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def plant_b(db):
    return Plant.objects.create(code="WG-B", name="Plant B", country="IT",
                                nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def pm_a(db, plant_a):
    return _make_user("wg_pm_a", GrcRole.PLANT_MANAGER, "single_plant", [plant_a])


@pytest.fixture
def org_user(db):
    return _make_user("wg_org", GrcRole.COMPLIANCE_OFFICER, "org")


# ── 1a. FK diretto al Plant nel body ─────────────────────────────────────────

@pytest.mark.django_db
def test_create_on_own_plant_allowed(pm_a, plant_a):
    resp = _client(pm_a).post("/api/v1/assets/network-zones/", {
        "plant": str(plant_a.id), "name": "Zona IT", "zone_type": "IT",
    }, format="json")
    assert resp.status_code == 201


@pytest.mark.django_db
def test_create_on_foreign_plant_denied(pm_a, plant_b):
    resp = _client(pm_a).post("/api/v1/assets/network-zones/", {
        "plant": str(plant_b.id), "name": "Zona intrusa", "zone_type": "IT",
    }, format="json")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_move_to_foreign_plant_denied(pm_a, plant_a, plant_b):
    from apps.assets.models import NetworkZone
    zone = NetworkZone.objects.create(plant=plant_a, name="Z", zone_type="IT")
    resp = _client(pm_a).patch(f"/api/v1/assets/network-zones/{zone.id}/", {
        "plant": str(plant_b.id),
    }, format="json")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_org_user_creates_anywhere(org_user, plant_b):
    resp = _client(org_user).post("/api/v1/assets/network-zones/", {
        "plant": str(plant_b.id), "name": "Zona org", "zone_type": "OT",
    }, format="json")
    assert resp.status_code == 201


# ── 1b. FK a oggetto correlato (plant_field con traversal) ───────────────────

@pytest.mark.django_db
def test_create_via_foreign_related_object_denied(pm_a, plant_a, plant_b):
    from apps.assets.models import AssetIT
    mine = AssetIT.objects.create(plant=plant_a, name="Server A", asset_type="IT")
    foreign = AssetIT.objects.create(plant=plant_b, name="Server B", asset_type="IT")
    # AssetDependency: plant_field = "from_asset__plant"
    resp = _client(pm_a).post("/api/v1/assets/dependencies/", {
        "from_asset": str(foreign.id), "to_asset": str(mine.id), "dep_type": "depends_on",
    }, format="json")
    assert resp.status_code == 403


# ── 1c. M2M di Plant nel body: serve accesso a TUTTI gli id ──────────────────

@pytest.mark.django_db
def test_course_with_foreign_plant_in_m2m_denied(pm_a, plant_a, plant_b):
    resp = _client(pm_a).post("/api/v1/training/courses/", {
        "title": "Corso misto", "plants": [str(plant_a.id), str(plant_b.id)],
    }, format="json")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_course_on_own_plant_allowed(pm_a, plant_a):
    resp = _client(pm_a).post("/api/v1/training/courses/", {
        "title": "Corso locale", "plants": [str(plant_a.id)],
    }, format="json")
    assert resp.status_code == 201


# ── 2. Directory siti / BU scoped ────────────────────────────────────────────

@pytest.mark.django_db
def test_plant_directory_lists_only_accessible(pm_a, plant_a, plant_b):
    resp = _client(pm_a).get("/api/v1/plants/plants/")
    assert resp.status_code == 200
    codes = {p["code"] for p in resp.data["results"]}
    assert codes == {"WG-A"}


@pytest.mark.django_db
def test_patch_foreign_plant_denied(pm_a, plant_b):
    resp = _client(pm_a).patch(f"/api/v1/plants/plants/{plant_b.id}/", {
        "name": "Hijacked",
    }, format="json")
    assert resp.status_code == 404  # fuori dal queryset scoped


@pytest.mark.django_db
def test_org_user_sees_all_plants(org_user, plant_a, plant_b):
    resp = _client(org_user).get("/api/v1/plants/plants/")
    codes = {p["code"] for p in resp.data["results"]}
    assert {"WG-A", "WG-B"} <= codes


# ── 3. Training scoped in lettura ────────────────────────────────────────────

@pytest.mark.django_db
def test_courses_foreign_hidden_global_visible(pm_a, plant_a, plant_b):
    from apps.training.models import TrainingCourse
    local = TrainingCourse.objects.create(title="Solo A")
    local.plants.add(plant_a)
    foreign = TrainingCourse.objects.create(title="Solo B")
    foreign.plants.add(plant_b)
    TrainingCourse.objects.create(title="Globale")  # senza plants

    resp = _client(pm_a).get("/api/v1/training/courses/")
    titles = {c["title"] for c in resp.data["results"]}
    assert titles == {"Solo A", "Globale"}


@pytest.mark.django_db
def test_enrollments_of_foreign_course_hidden(pm_a, plant_b):
    from apps.training.models import TrainingCourse, TrainingEnrollment
    course = TrainingCourse.objects.create(title="Solo B")
    course.plants.add(plant_b)
    someone = User.objects.create_user(username="wg_emp", email="e@test.com", password="x")
    TrainingEnrollment.objects.create(course=course, user=someone)

    resp = _client(pm_a).get("/api/v1/training/enrollments/")
    assert resp.data["count"] == 0


@pytest.mark.django_db
def test_completion_rate_foreign_course_404(pm_a, plant_b):
    from apps.training.models import TrainingCourse
    course = TrainingCourse.objects.create(title="Solo B")
    course.plants.add(plant_b)
    resp = _client(pm_a).get(f"/api/v1/training/courses/{course.id}/completion_rate/")
    assert resp.status_code == 404

"""Formazione a evidenze, fase 5: ruoli critici e organo di gestione.

Partecipanti nominativi scelti fra titolari di nomine e componenti degli organi
di governo, aggiornamento di UserCompetency (ISO 27001 cl. 7.2) e KPI
board_training_valid (NIS2 art. 20)."""
import base64
from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from apps.auth_grc.models import GrcRole, UserCompetency, UserPlantAccess

User = get_user_model()

URL_SESS = "/api/v1/training/sessions/"
URL_OPTIONS = f"{URL_SESS}participant-options/"
URL_BOARD = f"{URL_SESS}board-status/"

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


def _user(name, role=None, first="", last=""):
    u = User.objects.create_user(username=name, email=f"{name}@t.it", password="x",
                                 first_name=first, last_name=last)
    if role:
        UserPlantAccess.objects.create(user=u, role=role, scope_type="org")
    return u


def _nominate(user, role, plant=None, since=None, until=None):
    from apps.governance.models import RoleAssignment
    return RoleAssignment.objects.create(
        user=user, role=role, scope_type="plant" if plant else "org",
        scope_id=plant.pk if plant else None,
        valid_from=since or date(2025, 1, 1), valid_until=until,
    )


def _body(name="CdA", kind="cda", plants=()):
    from apps.governance.models import SecurityCommittee
    body = SecurityCommittee.objects.create(name=name, committee_type=kind)
    body.plants.set(plants)
    return body


def _member(body, name, user=None, since=None, until=None):
    from apps.governance.models import CommitteeMember
    return CommitteeMember.objects.create(
        committee=body, full_name=name, user=user,
        valid_from=since or date(2025, 1, 1), valid_until=until,
    )


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


def _course(**kw):
    from apps.training.models import TrainingCourse
    kw.setdefault("title", "Cyber per il CdA")
    kw.setdefault("kind", "corso")
    kw.setdefault("audience_kind", "organo_gestione")
    kw.setdefault("validity_months", 12)
    return TrainingCourse.objects.create(**kw)


def _register(client, course, plant, users=(), members=(), held_on=None, **extra):
    data = {
        "course": str(course.pk),
        "plant": str(plant.pk),
        "held_on": (held_on or timezone.localdate() - timedelta(days=3)).isoformat(),
        "file": _proof(),
        "participant_users": [str(u.pk) for u in users],
        "participant_members": [str(m.pk) for m in members],
    }
    data.update(extra)
    return client.post(URL_SESS, data, format="multipart")


# ── Chi si può scegliere ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_participant_options_follow_site_and_dates(plant, plant_b):
    from apps.training.services import participant_options

    ciso = _user("ciso", first="Anna", last="Neri")
    _nominate(ciso, "ciso")                                   # org: copre ogni sito
    _nominate(ciso, "dpo", plant=plant)
    other_site = _user("psa")
    _nominate(other_site, "plant_security_officer", plant=plant_b)
    ended = _user("old")
    _nominate(ended, "ciso", plant=plant, until=date(2025, 6, 30))

    org_body = _body("CdA gruppo")
    _member(org_body, "Mario Rossi")
    _member(org_body, "Ex consigliere", until=date(2025, 6, 30))
    _member(_body("CdA B", plants=[plant_b]), "Solo B")
    _member(_body("Comitato A", kind="comitato", plants=[plant]), "Luca Bianchi")

    opts = participant_options(plant, date(2026, 9, 1))
    assert opts["role_holders"] == [
        {"user_id": str(ciso.pk), "name": "Anna Neri", "roles": ["ciso", "dpo"]},
    ]
    names = {m["name"]: m for m in opts["members"]}
    assert set(names) == {"Mario Rossi", "Luca Bianchi"}
    assert names["Mario Rossi"]["management_body"] is True
    assert names["Luca Bianchi"]["management_body"] is False

    # Alla data dell'erogazione, non a oggi.
    past = participant_options(plant, date(2025, 3, 1))
    assert {h["user_id"] for h in past["role_holders"]} == {str(ciso.pk), str(ended.pk)}


@pytest.mark.django_db
def test_participant_options_endpoint_only_for_site_managers(co, plant):
    auditor = _user("aud", GrcRole.INTERNAL_AUDITOR)
    assert _client(auditor).get(URL_OPTIONS, {"plant": str(plant.pk)}).status_code == 403
    r = _client(co).get(URL_OPTIONS, {"plant": str(plant.pk), "held_on": "2026-09-01"})
    assert r.status_code == 200
    assert set(r.data) == {"role_holders", "members"}
    assert _client(co).get(URL_OPTIONS).status_code == 400


# ── Registrazione ───────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_named_session_records_participants_and_counts(co, plant):
    from apps.training.models import TrainingSession
    from core.audit import AuditLog

    ciso = _user("ciso", first="Anna", last="Neri")
    _nominate(ciso, "ciso")
    body = _body()
    rossi = _member(body, "Mario Rossi")
    course = _course(audience_kind="ruoli_critici")

    r = _register(_client(co), course, plant, users=[ciso], members=[rossi])
    assert r.status_code == 201, r.data
    session = TrainingSession.objects.get(pk=r.data["id"])
    assert (session.trained_count, session.target_count) == (2, 2)
    detail = {p["name"]: p for p in r.data["participants_detail"]}
    assert detail["Anna Neri"]["roles"] == ["ciso"]
    assert detail["Mario Rossi"]["committee"] == "CdA"

    # Audit: solo id e conteggi, nessun nome (regola #11).
    log = AuditLog.objects.filter(action_code="training.session.register").latest("timestamp_utc")
    assert log.payload["participants"] == 2
    assert "Rossi" not in str(log.payload) and "Neri" not in str(log.payload)


@pytest.mark.django_db
def test_member_with_account_and_nomination_is_one_participant(co, plant):
    ad = _user("ad", first="Paolo", last="Verdi")
    _nominate(ad, "isms_manager")
    member = _member(_body(), "Paolo Verdi", user=ad)

    r = _register(_client(co), _course(), plant, users=[ad], members=[member], target_count=5)
    assert r.status_code == 201, r.data
    assert r.data["trained_count"] == 1 and r.data["target_count"] == 5
    [p] = r.data["participants_detail"]
    assert p["member_id"] == str(member.pk) and p["user_id"] == str(ad.pk)
    assert p["roles"] == ["isms_manager"]


@pytest.mark.django_db
def test_named_session_validation(co, plant, plant_b):
    from apps.training.models import TrainingAudience

    client = _client(co)
    course = _course()
    stranger = _user("x")
    assert "participant_users" in _register(client, course, plant, users=[stranger]).data
    other = _member(_body("CdA B", plants=[plant_b]), "Solo B")
    assert "participant_members" in _register(client, course, plant, members=[other]).data
    # Nessun partecipante.
    assert "participant_users" in _register(client, course, plant).data
    # Gruppi di destinatari su un corso nominativo.
    member = _member(_body(), "Mario Rossi")
    aud = TrainingAudience.objects.create(plant=plant, name="Uffici", headcount=10,
                                          headcount_updated_at=timezone.localdate())
    r = _register(client, course, plant, members=[member], audiences=[str(aud.pk)])
    assert "audiences" in r.data
    # Nominativi su un corso per il personale: solo conteggi.
    general = _course(title="Awareness", audience_kind="generale")
    r = _register(client, general, plant, members=[member], target_count=10, trained_count=5)
    assert "participant_users" in r.data


@pytest.mark.django_db
def test_participants_cannot_be_edited(co, plant):
    member = _member(_body(), "Mario Rossi")
    client = _client(co)
    r = _register(client, _course(), plant, members=[member])
    sid = r.data["id"]
    r = client.patch(f"{URL_SESS}{sid}/", {"participant_members": []}, format="json")
    assert r.status_code == 400 and "participant_users" in r.data
    r = client.patch(f"{URL_SESS}{sid}/", {"trained_count": 3, "target_count": 3}, format="json")
    assert r.status_code == 400 and "trained_count" in r.data
    r = client.patch(f"{URL_SESS}{sid}/", {"notes": "ok"}, format="json")
    assert r.status_code == 200


# ── Competenze (ISO 27001 cl. 7.2) ─────────────────────────────────────────

def _competency_course(level=2, **kw):
    return _course(audience_kind="ruoli_critici", competency="NIS2 Compliance",
                   competency_level=level, **kw)


@pytest.mark.django_db
def test_session_creates_user_competency_backed_by_evidence(co, plant):
    ciso = _user("ciso")
    _nominate(ciso, "ciso")
    held = timezone.localdate() - timedelta(days=10)
    r = _register(_client(co), _competency_course(), plant, users=[ciso], held_on=held)
    assert r.status_code == 201, r.data
    uc = UserCompetency.objects.get(user=ciso, competency="NIS2 Compliance")
    assert uc.level == 2 and uc.evidence_type == "training"
    assert str(uc.evidence_id) == str(r.data["evidence"])
    assert uc.obtained_at == held
    assert uc.valid_until.isoformat() == str(r.data["evidence_valid_until"])
    assert uc.verified_by == co


@pytest.mark.django_db
def test_competency_is_not_lowered_or_replaced_by_older_proof(co, plant):
    ciso = _user("ciso")
    _nominate(ciso, "ciso")
    cert = UserCompetency.objects.create(user=ciso, competency="NIS2 Compliance", level=3,
                                         evidence_type="certification",
                                         obtained_at=date(2026, 1, 10))
    client = _client(co)
    assert _register(client, _competency_course(level=2), plant, users=[ciso]).status_code == 201
    cert.refresh_from_db()
    assert cert.level == 3 and cert.evidence_type == "certification"

    cert.level = 2
    cert.save()
    old = date(2025, 12, 1)
    assert _register(client, _competency_course(level=2, title="Vecchio"), plant,
                     users=[ciso], held_on=old).status_code == 201
    cert.refresh_from_db()
    assert cert.obtained_at == date(2026, 1, 10) and cert.evidence_id is None


@pytest.mark.django_db
def test_deleting_session_reverts_competency(co, plant):
    ciso = _user("ciso")
    _nominate(ciso, "ciso")
    client = _client(co)
    course = _competency_course()

    # Nata dall'erogazione → eliminata con essa, e si può registrare di nuovo.
    r = _register(client, course, plant, users=[ciso])
    assert client.delete(f"{URL_SESS}{r.data['id']}/").status_code == 204
    assert not UserCompetency.objects.filter(user=ciso).exists()
    assert _register(client, course, plant, users=[ciso]).status_code == 201
    assert UserCompetency.objects.filter(user=ciso).count() == 1


@pytest.mark.django_db
def test_deleting_sessions_restores_previous_state_through_chain(co, plant):
    ciso = _user("ciso")
    _nominate(ciso, "ciso")
    client = _client(co)
    course = _competency_course(level=1)
    original = UserCompetency.objects.create(
        user=ciso, competency="NIS2 Compliance", level=1, evidence_type="experience",
        obtained_at=date(2024, 5, 1), certification_body="Ente X",
    )
    today = timezone.localdate()
    first = _register(client, course, plant, users=[ciso], held_on=today - timedelta(days=20))
    second = _register(client, course, plant, users=[ciso], held_on=today - timedelta(days=5))
    original.refresh_from_db()
    assert str(original.evidence_id) == str(second.data["evidence"])

    # Eliminare la prima non tocca la competenza, che poggia sulla seconda.
    assert client.delete(f"{URL_SESS}{first.data['id']}/").status_code == 204
    original.refresh_from_db()
    assert str(original.evidence_id) == str(second.data["evidence"])

    # Eliminata anche la seconda si risale oltre la prima, già eliminata.
    assert client.delete(f"{URL_SESS}{second.data['id']}/").status_code == 204
    original.refresh_from_db()
    assert original.deleted_at is None
    assert original.evidence_id is None and original.evidence_type == "experience"
    assert original.obtained_at == date(2024, 5, 1) and original.certification_body == "Ente X"


@pytest.mark.django_db
def test_moving_held_on_moves_competency_dates(co, plant):
    ciso = _user("ciso")
    _nominate(ciso, "ciso")
    client = _client(co)
    r = _register(client, _competency_course(), plant, users=[ciso])
    new_day = timezone.localdate() - timedelta(days=30)
    r = client.patch(f"{URL_SESS}{r.data['id']}/", {"held_on": new_day.isoformat()}, format="json")
    assert r.status_code == 200, r.data
    uc = UserCompetency.objects.get(user=ciso)
    assert uc.obtained_at == new_day
    assert uc.valid_until == new_day.replace(year=new_day.year + 1)


# ── Organo di gestione (NIS2 art. 20) ──────────────────────────────────────

def _named_session(course, plant, held_on, members=(), users=()):
    from apps.training.models import TrainingParticipant, TrainingSession
    s = TrainingSession.objects.create(course=course, plant=plant, held_on=held_on,
                                       target_count=1, trained_count=1)
    for m in members:
        TrainingParticipant.objects.create(session=s, committee_member=m, user=m.user)
    for u in users:
        TrainingParticipant.objects.create(session=s, user=u)
    return s


@pytest.mark.django_db
def test_board_training_counts_valid_training_of_serving_members(plant, plant_b):
    from apps.training.services import board_training

    today = date(2026, 9, 21)
    body = _body()                               # di organizzazione
    trained = _member(body, "Aldo Formato")
    expired = _member(body, "Bruno Scaduto")
    by_account = _member(body, "Carla Account", user=_user("carla"))
    _member(body, "Dario Mai")
    _member(body, "Ex", until=date(2026, 1, 1))  # non più in carica
    _member(_body("Comitato", kind="comitato"), "Non CdA")
    board_b = _member(_body("CdA B", plants=[plant_b]), "Solo B")

    course = _course()
    _named_session(course, plant, date(2026, 3, 1), members=[trained])
    _named_session(course, plant, date(2025, 6, 1), members=[expired])
    # Scelta fra i titolari di nomine: riconosciuta tramite l'account.
    _named_session(course, plant, date(2026, 5, 1), users=[by_account.user])
    # Un corso per ruoli critici non conta per il CdA.
    _named_session(_course(title="Ruoli", audience_kind="ruoli_critici"), plant,
                   date(2026, 5, 1), members=[board_b])

    res = board_training(plant, today)
    assert (res["total"], res["trained"], res["pct"]) == (4, 2, 50.0)
    rows = {m["full_name"]: m for m in res["members"]}
    assert rows["Aldo Formato"]["valid_until"] == date(2027, 3, 1)
    assert rows["Bruno Scaduto"]["trained"] is False
    assert rows["Carla Account"]["trained"] is True

    assert board_training(plant_b, today)["total"] == 5
    assert board_training(None, today)["total"] == 5


@pytest.mark.django_db
def test_board_training_ignores_deleted_sessions(plant):
    from apps.training.services import board_training

    member = _member(_body(), "Aldo")
    s = _named_session(_course(), plant, date(2026, 3, 1), members=[member])
    assert board_training(plant, date(2026, 9, 21))["trained"] == 1
    s.soft_delete()
    assert board_training(plant, date(2026, 9, 21))["trained"] == 0


@pytest.mark.django_db
def test_board_training_kpi_connector(plant):
    from apps.tasks.kpi_catalog import KPI_CATALOG
    from apps.tasks.kpi_connectors import INTERNAL_CONNECTORS, board_training_valid

    assert KPI_CATALOG["board_training_valid"]["source"] == "internal"
    assert INTERNAL_CONNECTORS["board_training_valid"] is board_training_valid
    week = timezone.localdate()
    assert board_training_valid(plant, week)["value"] is None

    member = _member(_body(), "Aldo")
    _member(_body(name="CdA 2"), "Bea")
    _named_session(_course(), plant, timezone.localdate() - timedelta(days=5), members=[member])
    res = board_training_valid(plant, week)
    assert res["value"] == 50.0 and res["run_count"] == 2
    assert "Aldo" not in res["note"]


@pytest.mark.django_db
def test_board_status_endpoint_and_reporting(co, plant, plant_b):
    from apps.reporting.services import _training

    member = _member(_body(), "Aldo")
    _named_session(_course(), plant, timezone.localdate() - timedelta(days=5), members=[member])

    r = _client(co).get(URL_BOARD, {"plant": str(plant.pk)})
    assert r.status_code == 200 and r.data["trained"] == 1
    assert r.data["members"][0]["full_name"] == "Aldo"

    # Utente limitato a un altro sito: niente dati del sito né aggregato.
    pm = _user("pm")
    access = UserPlantAccess.objects.create(user=pm, role=GrcRole.PLANT_MANAGER,
                                            scope_type="single_plant")
    access.scope_plants.set([plant_b])
    assert _client(pm).get(URL_BOARD, {"plant": str(plant.pk)}).status_code == 403
    assert _client(pm).get(URL_BOARD).status_code == 403

    board = _training(plant)["board"]
    assert board == {"total": 1, "trained": 1, "pct": 100.0}


@pytest.mark.django_db
def test_audit_pack_exports_participants_and_board(co, plant, tmp_path):
    import csv

    from apps.audit_prep.audit_pack import _collect_training

    member = _member(_body(), "Aldo Formato")
    r = _register(_client(co), _course(), plant, members=[member])
    assert r.status_code == 201, r.data
    summary = _collect_training(tmp_path, plant)
    assert summary["board_training_pct"] == 100.0
    with (tmp_path / "07_training" / "sessions.csv").open(encoding="utf-8") as fp:
        [row] = list(csv.DictReader(fp))
    assert row["participants"] == "Aldo Formato"
    with (tmp_path / "07_training" / "board_training.csv").open(encoding="utf-8") as fp:
        [row] = list(csv.DictReader(fp))
    assert row["full_name"] == "Aldo Formato" and row["trained"] == "True"


@pytest.mark.django_db
def test_course_competency_fields_and_options(co):
    from apps.auth_grc.models import RoleCompetencyRequirement

    RoleCompetencyRequirement.objects.create(grc_role="ciso", competency="NIS2 Compliance")
    RoleCompetencyRequirement.objects.create(grc_role="compliance_officer", competency="NIS2 Compliance")
    RoleCompetencyRequirement.objects.create(grc_role="ciso", competency="Incident Response")
    client = _client(co)
    r = client.get("/api/v1/training/courses/competency-options/")
    assert r.data == ["Incident Response", "NIS2 Compliance"]
    r = client.post("/api/v1/training/courses/", {
        "title": "NIS2 per il CISO", "audience_kind": "ruoli_critici",
        "competency": "NIS2 Compliance", "competency_level": 3,
    }, format="json")
    assert r.status_code == 201, r.data
    assert r.data["competency"] == "NIS2 Compliance" and r.data["competency_level"] == 3

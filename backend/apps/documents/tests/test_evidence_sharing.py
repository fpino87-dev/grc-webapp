"""Condivisione delle evidenze fra siti (stessa regola dei documenti).

L'evidenza resta del sito proprietario; i siti con cui è condivisa la vedono,
la scaricano e la collegano ai propri controlli, ma non la modificano, non la
eliminano e non ne cambiano la condivisione.
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.auth_grc.models import GrcRole, UserPlantAccess
from apps.controls.models import Control, ControlInstance, Framework
from apps.documents.models import Evidence
from apps.plants.models import Plant, PlantFramework
from core.audit import AuditLog

User = get_user_model()

URL_EV = "/api/v1/documents/evidences/"
URL_CTRL = "/api/v1/controls/instances/"


def make_user(username, role, scope_type="org", plants=()):
    u = User.objects.create_user(username=username, email=f"{username}@test.com", password="x")
    access = UserPlantAccess.objects.create(user=u, role=role, scope_type=scope_type)
    for p in plants:
        access.scope_plants.add(p)
    return u


def client_for(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _plant(code):
    return Plant.objects.create(code=code, name=f"Plant {code}", country="IT",
                                nis2_scope="importante", status="attivo")


@pytest.fixture
def env(db):
    plant_a, plant_b, plant_c = _plant("SH-A"), _plant("SH-B"), _plant("SH-C")
    fw = Framework.objects.create(code="ISO27001", name="ISO", version="2022",
                                  published_at=timezone.localdate())
    ctrl = Control.objects.create(framework=fw, external_id="A.5.1",
                                  translations={"it": {"title": "Politiche"}},
                                  evidence_requirement={})
    for p in (plant_a, plant_b):
        PlantFramework.objects.create(plant=p, framework=fw,
                                      active_from=timezone.localdate(), level="L2", active=True)
    inst_b = ControlInstance.objects.create(plant=plant_b, control=ctrl, status="non_valutato")
    ev_a = Evidence.objects.create(title="Report pentest", evidence_type="report", plant=plant_a)
    return {
        "plant_a": plant_a, "plant_b": plant_b, "plant_c": plant_c,
        "inst_b": inst_b, "ev_a": ev_a,
        "user_a": make_user("sh_a", GrcRole.COMPLIANCE_OFFICER, "single_plant", [plant_a]),
        "user_b": make_user("sh_b", GrcRole.COMPLIANCE_OFFICER, "single_plant", [plant_b]),
        "org": make_user("sh_org", GrcRole.COMPLIANCE_OFFICER, "org"),
    }


def _titles(resp):
    return {r["title"] for r in resp.data["results"]}


@pytest.mark.django_db
def test_owner_shares_evidence_and_audit_is_logged(env):
    resp = client_for(env["user_a"]).post(
        f"{URL_EV}{env['ev_a'].id}/share/",
        {"plant_ids": [str(env["plant_b"].id), str(env["plant_a"].id)]}, format="json",
    )
    assert resp.status_code == 200
    # un utente di sito agisce solo sui siti a cui ha accesso; il sito
    # proprietario non entra mai nell'elenco
    assert list(env["ev_a"].shared_plants.all()) == []

    resp = client_for(env["org"]).post(
        f"{URL_EV}{env['ev_a'].id}/share/",
        {"plant_ids": [str(env["plant_b"].id), str(env["plant_a"].id)]}, format="json",
    )
    assert resp.status_code == 200
    assert [p["code"] for p in resp.data["shared_with"]] == ["SH-B"]
    assert list(env["ev_a"].shared_plants.all()) == [env["plant_b"]]
    log = AuditLog.objects.filter(action_code="evidence.shared", entity_id=env["ev_a"].pk).latest("timestamp_utc")
    assert log.payload["added"] == [str(env["plant_b"].id)]


@pytest.mark.django_db
def test_site_user_keeps_shares_outside_own_perimeter(env):
    env["ev_a"].shared_plants.add(env["plant_b"])
    user_ac = make_user("sh_ac", GrcRole.COMPLIANCE_OFFICER, "plant_list",
                        [env["plant_a"], env["plant_c"]])
    resp = client_for(user_ac).post(
        f"{URL_EV}{env['ev_a'].id}/share/", {"plant_ids": [str(env["plant_c"].id)]}, format="json",
    )
    assert resp.status_code == 200
    # la condivisione con B (fuori dal suo perimetro) non viene toccata
    assert set(env["ev_a"].shared_plants.all()) == {env["plant_b"], env["plant_c"]}


@pytest.mark.django_db
def test_shared_evidence_is_visible_only_to_shared_site(env):
    c_b = client_for(env["user_b"])
    assert "Report pentest" not in _titles(c_b.get(URL_EV))
    assert c_b.get(f"{URL_EV}{env['ev_a'].id}/").status_code == 404

    env["ev_a"].shared_plants.add(env["plant_b"])
    resp = c_b.get(URL_EV, {"plant": str(env["plant_b"].id)})
    row = next(r for r in resp.data["results"] if r["title"] == "Report pentest")
    assert row["is_shared_with_current"] is True
    assert row["can_manage"] is False
    assert [p["code"] for p in row["shared_plant_names"]] == ["SH-B"]

    # il filtro per sito di un terzo sito non la mostra
    resp = client_for(env["org"]).get(URL_EV, {"plant": str(env["plant_c"].id)})
    assert "Report pentest" not in _titles(resp)
    # per il proprietario non è "condivisa con il sito corrente"
    resp = client_for(env["user_a"]).get(URL_EV, {"plant": str(env["plant_a"].id)})
    row = next(r for r in resp.data["results"] if r["title"] == "Report pentest")
    assert row["is_shared_with_current"] is False
    assert row["can_manage"] is True


@pytest.mark.django_db
def test_shared_site_cannot_edit_delete_or_reshare(env):
    env["ev_a"].shared_plants.add(env["plant_b"])
    c_b = client_for(env["user_b"])
    url = f"{URL_EV}{env['ev_a'].id}/"
    assert c_b.patch(url, {"title": "Cambiato"}, format="json").status_code == 404
    assert c_b.delete(url).status_code == 404
    assert c_b.post(f"{url}share/", {"plant_ids": []}, format="json").status_code == 404
    env["ev_a"].refresh_from_db()
    assert env["ev_a"].title == "Report pentest"
    assert env["ev_a"].deleted_at is None
    assert list(env["ev_a"].shared_plants.all()) == [env["plant_b"]]


@pytest.mark.django_db
def test_link_to_control_requires_sharing(env):
    c_b = client_for(env["user_b"])
    url = f"{URL_CTRL}{env['inst_b'].id}/link_evidence/"
    body = {"evidence_id": str(env["ev_a"].id)}
    assert c_b.post(url, body, format="json").status_code == 404

    env["ev_a"].shared_plants.add(env["plant_b"])
    assert c_b.post(url, body, format="json").status_code == 200
    assert list(env["inst_b"].evidences.all()) == [env["ev_a"]]


@pytest.mark.django_db
def test_patch_m2m_accepts_shared_evidence_only(env):
    c_b = client_for(env["user_b"])
    url = f"{URL_CTRL}{env['inst_b'].id}/"
    body = {"evidences": [str(env["ev_a"].id)]}
    assert c_b.patch(url, body, format="json").status_code == 400

    env["ev_a"].shared_plants.add(env["plant_b"])
    assert c_b.patch(url, body, format="json").status_code == 200
    assert env["inst_b"].evidences.count() == 1


@pytest.mark.django_db
def test_org_wide_evidence_cannot_be_shared(env):
    ev = Evidence.objects.create(title="Org", evidence_type="report", plant=None)
    resp = client_for(env["org"]).post(
        f"{URL_EV}{ev.id}/share/", {"plant_ids": [str(env["plant_b"].id)]}, format="json",
    )
    assert resp.status_code == 400
    assert ev.shared_plants.count() == 0


@pytest.mark.django_db
def test_share_rejects_malformed_plant_ids(env):
    resp = client_for(env["org"]).post(
        f"{URL_EV}{env['ev_a'].id}/share/", {"plant_ids": ["non-un-uuid"]}, format="json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_bcp_test_evidence_accepts_shared_only(env):
    from django.core.exceptions import ValidationError

    from apps.bcp.models import BcpPlan
    from apps.bcp.services import _evidences_for_plan

    plan = BcpPlan.objects.create(plant=env["plant_b"], title="Piano B")
    with pytest.raises(ValidationError):
        _evidences_for_plan(plan, [env["ev_a"].id])

    env["ev_a"].shared_plants.add(env["plant_b"])
    assert _evidences_for_plan(plan, [env["ev_a"].id]) == [env["ev_a"]]


@pytest.mark.django_db
def test_audit_pack_includes_evidence_shared_with_site(env, tmp_path):
    from apps.audit_prep.audit_pack import _collect_evidences

    assert _collect_evidences(tmp_path / "prima", env["plant_b"], [])["evidences_total"] == 0
    env["ev_a"].shared_plants.add(env["plant_b"])
    assert _collect_evidences(tmp_path / "dopo", env["plant_b"], [])["evidences_total"] == 1
    assert _collect_evidences(tmp_path / "terzo", env["plant_c"], [])["evidences_total"] == 0

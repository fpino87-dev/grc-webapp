"""Matrice Accessi & Responsabilità (Reporting / access review A.9.2.5) — Fase 1."""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.auth_grc.models import GrcRole, UserPlantAccess

User = get_user_model()

URL = "/api/v1/reporting/access-matrix/"


def _client(role):
    safe = role.replace("_", "")
    u = User.objects.create_user(username=f"am_{safe}", email=f"{safe}@am.test", password="x")
    UserPlantAccess.objects.create(user=u, role=role, scope_type="org")
    c = APIClient()
    c.force_authenticate(user=u)
    return c, u


@pytest.fixture
def topo(db):
    from apps.plants.models import BusinessUnit, Plant
    bu = BusinessUnit.objects.create(code="AMBU", name="BU AM")
    pa = Plant.objects.create(code="AMA", name="Plant AMA", country="IT", bu=bu,
                              nis2_scope="importante", status="attivo")
    pb = Plant.objects.create(code="AMB", name="Plant AMB", country="IT", bu=bu,
                              nis2_scope="importante", status="attivo")
    return bu, pa, pb


@pytest.mark.django_db
def test_matrix_aggregates_access_and_responsibility(topo):
    from apps.governance.models import NormativeRole, RoleAssignment
    from apps.reporting.services import access_matrix
    bu, pa, pb = topo

    worker = User.objects.create_user(username="amw", email="amw@am.test", password="x")
    # accesso solo a pa (plant_list); responsabilità CISO su pb → senza accesso a pb
    acc = UserPlantAccess.objects.create(user=worker, role=GrcRole.PLANT_MANAGER, scope_type="single_plant")
    acc.scope_plants.add(pa)
    RoleAssignment.objects.create(user=worker, role=NormativeRole.CISO,
                                  scope_type="plant", scope_id=pb.id, valid_from=timezone.localdate())

    data = access_matrix(None, "it")
    kinds = {(r["user_id"], r["kind"]) for r in data["rows"] if r["user_id"] == str(worker.id)}
    assert (str(worker.id), "access") in kinds
    assert (str(worker.id), "responsibility") in kinds
    # responsabilità su pb senza accesso a pb → flag
    resp_row = next(r for r in data["rows"]
                    if r["user_id"] == str(worker.id) and r["kind"] == "responsibility")
    assert "responsibility_without_access" in resp_row["flags"]


@pytest.mark.django_db
def test_matrix_plant_filter_scopes_rows(topo):
    from apps.reporting.services import access_matrix
    bu, pa, pb = topo
    only_a = User.objects.create_user(username="amA", email="ama@am.test", password="x")
    acc = UserPlantAccess.objects.create(user=only_a, role=GrcRole.CONTROL_OWNER, scope_type="single_plant")
    acc.scope_plants.add(pa)

    data_b = access_matrix(str(pb.id), "it")
    assert all(r["user_id"] != str(only_a.id) for r in data_b["rows"])  # non copre pb
    data_a = access_matrix(str(pa.id), "it")
    assert any(r["user_id"] == str(only_a.id) for r in data_a["rows"])


@pytest.mark.django_db
def test_inactive_user_flagged():
    from apps.reporting.services import access_matrix
    u = User.objects.create_user(username="aminact", email="inact@am.test", password="x", is_active=False)
    UserPlantAccess.objects.create(user=u, role=GrcRole.CONTROL_OWNER, scope_type="org")
    data = access_matrix(None, "it")
    row = next(r for r in data["rows"] if r["user_id"] == str(u.id))
    assert "inactive_user" in row["flags"]


@pytest.mark.django_db
def test_permission_restricted_to_governance_and_audit():
    # auditor: ok
    auditor, _ = _client(GrcRole.INTERNAL_AUDITOR)
    assert auditor.get(URL).status_code == 200
    # ruolo operativo: negato (non conduce access review)
    owner, _ = _client(GrcRole.CONTROL_OWNER)
    assert owner.get(URL).status_code == 403
    rm, _ = _client(GrcRole.RISK_MANAGER)
    assert rm.get(URL).status_code == 403


@pytest.mark.django_db
def test_security_committees_in_report(topo):
    """Organi di governo: componenti in carica (anche senza account), filtro
    per sito, segnalazioni su account disattivati e presidente mancante."""
    from datetime import date, timedelta

    from apps.governance.models import CommitteeMember, SecurityCommittee
    from apps.reporting.services import access_matrix
    bu, pa, pb = topo

    member = User.objects.create_user(username="commemb", email="cm@am.test",
                                       first_name="Comm", last_name="Member", password="x", is_active=False)
    cda = SecurityCommittee.objects.create(name="CdA", committee_type="cda")
    CommitteeMember.objects.create(committee=cda, full_name="Paola Neri", position="Presidente CdA",
                                   body_role="presidente", valid_from=date(2025, 1, 1))
    CommitteeMember.objects.create(committee=cda, full_name="Comm Member", user=member,
                                   valid_from=date(2025, 1, 1))
    CommitteeMember.objects.create(committee=cda, full_name="Ex Consigliere",
                                   valid_from=date(2020, 1, 1), valid_until=date.today() - timedelta(days=1))
    site = SecurityCommittee.objects.create(name="Comitato B", committee_type="comitato")
    site.plants.add(pb)

    data = access_matrix(None, "it")
    assert data["summary"]["committees"] == 2
    row = next(c for c in data["committees"] if c["name"] == "CdA")
    assert row["is_management_body"] and row["covers_all"]
    assert [m["name"] for m in row["members"]] == ["Paola Neri", "Comm Member"]  # presidente prima, ex escluso
    assert row["members"][1]["flags"] == ["inactive_user"]
    assert row["members"][0]["has_account"] is False
    assert next(c for c in data["committees"] if c["name"] == "Comitato B")["flags"] == ["no_members"]

    # filtro sito: il comitato del sito B non compare sul sito A
    assert [c["name"] for c in access_matrix(str(pa.id), "it")["committees"]] == ["CdA"]


@pytest.mark.django_db
def test_committee_empty_state_when_none():
    from apps.reporting.services import access_matrix
    data = access_matrix(None, "it")
    assert data["committees"] == []
    assert data["summary"]["committees"] == 0


@pytest.mark.django_db
def test_csv_export():
    client, _ = _client(GrcRole.COMPLIANCE_OFFICER)
    resp = client.get(f"{URL}?export=csv")
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("text/csv")
    assert b"attachment" in resp["Content-Disposition"].encode()

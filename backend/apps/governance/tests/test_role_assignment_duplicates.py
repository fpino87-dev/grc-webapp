"""Assegnazioni di ruolo duplicate: pulizia, vincolo DB, conflitti, API e comando."""
from datetime import timedelta
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from apps.governance.models import RoleAssignment
from apps.governance.services import (
    cleanup_duplicate_role_assignments,
    find_duplicate_role_assignments,
    find_single_holder_conflicts,
)
from core.audit import AuditLog

User = get_user_model()
URL = "/api/v1/governance/role-assignments/"
pytestmark = pytest.mark.django_db


@pytest.fixture
def org_user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="dup_user", email="dup@test.com", password="test")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="dup_other", email="dup_other@test.com", password="test")


@pytest.fixture
def client(org_user):
    c = APIClient()
    c.force_authenticate(user=org_user)
    return c


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="DUP", name="Plant duplicati", country="IT", nis2_scope="essenziale", status="attivo")


@pytest.fixture
def without_open_constraint():
    """Toglie il vincolo per ricreare i doppioni nati prima del fix. La DDL è
    dentro la transazione del test e viene annullata con il rollback."""
    constraint = next(c for c in RoleAssignment._meta.constraints if c.name == "uniq_open_role_assignment")
    with connection.schema_editor() as editor:
        editor.remove_constraint(RoleAssignment, constraint)
    yield


def _assign(user, role="nis2_contact", scope_type="plant", scope_id=None, valid_from=None, valid_until=None):
    return RoleAssignment.objects.create(
        user=user, role=role, scope_type=scope_type, scope_id=scope_id,
        valid_from=valid_from or timezone.localdate(), valid_until=valid_until,
    )


def test_cleanup_keeps_oldest_and_audits_each_removal(without_open_constraint, org_user, plant):
    today = timezone.localdate()
    oldest = _assign(org_user, scope_id=plant.id, valid_from=today - timedelta(days=90))
    dup1 = _assign(org_user, scope_id=plant.id)
    dup2 = _assign(org_user, scope_id=plant.id)
    terminated = _assign(org_user, scope_id=plant.id, valid_from=today - timedelta(days=400), valid_until=today - timedelta(days=100))

    groups = find_duplicate_role_assignments()
    assert len(groups) == 1
    assert groups[0]["keep"].pk == oldest.pk
    assert {d.pk for d in groups[0]["remove"]} == {dup1.pk, dup2.pk}

    assert cleanup_duplicate_role_assignments(org_user) == 2
    assert set(RoleAssignment.objects.filter(scope_id=plant.id).values_list("pk", flat=True)) == {oldest.pk, terminated.pk}
    audits = AuditLog.objects.filter(action_code="governance.role_assignment.duplicate_removed")
    assert {a.entity_id for a in audits} == {dup1.pk, dup2.pk}
    assert all(a.payload["kept_assignment"] == str(oldest.pk) for a in audits)

    # idempotente
    assert find_duplicate_role_assignments() == []
    assert cleanup_duplicate_role_assignments(org_user) == 0


def test_constraint_blocks_second_open_assignment_same_user(org_user, plant):
    _assign(org_user, scope_id=plant.id)
    with pytest.raises(IntegrityError), transaction.atomic():
        _assign(org_user, scope_id=plant.id)
    # anche per le nomine org, dove scope_id è NULL
    _assign(org_user, role="ciso", scope_type="org")
    with pytest.raises(IntegrityError), transaction.atomic():
        _assign(org_user, role="ciso", scope_type="org")


def test_constraint_allows_renomination_after_termination(org_user, plant):
    today = timezone.localdate()
    _assign(org_user, scope_id=plant.id, valid_from=today - timedelta(days=30), valid_until=today - timedelta(days=1))
    _assign(org_user, scope_id=plant.id)
    assert RoleAssignment.objects.filter(scope_id=plant.id).count() == 2


def test_api_rejects_same_user_twice_on_multi_holder_role(client, org_user, plant):
    payload = {
        "user": org_user.id, "role": "control_owner", "scope_type": "plant",
        "scope_id": str(plant.id), "valid_from": str(timezone.localdate()),
    }
    assert client.post(URL, payload, format="json").status_code == 201
    r2 = client.post(URL, payload, format="json")
    assert r2.status_code == 400
    assert "role" in r2.json()
    assert RoleAssignment.objects.filter(role="control_owner", scope_id=plant.id).count() == 1


def test_single_holder_conflicts_between_different_users_are_reported(org_user, other_user, plant):
    _assign(org_user, scope_id=plant.id)
    _assign(other_user, scope_id=plant.id)
    # ruolo multi-titolare: più titolari sono legittimi, nessun conflitto
    _assign(org_user, role="control_owner", scope_id=plant.id)
    _assign(other_user, role="control_owner", scope_id=plant.id)

    conflicts = find_single_holder_conflicts()
    assert conflicts == [{
        "role": "nis2_contact", "scope_type": "plant", "scope_id": plant.id,
        "user_ids": sorted([org_user.id, other_user.id]),
    }]


def test_replace_role_with_user_already_holding_it_returns_400(client, org_user, other_user, plant):
    a1 = _assign(org_user, role="control_owner", scope_id=plant.id)
    _assign(other_user, role="control_owner", scope_id=plant.id)
    resp = client.post(f"{URL}{a1.id}/sostituisci/", {"new_user_id": other_user.id, "reason": "cambio"}, format="json")
    assert resp.status_code == 400
    a1.refresh_from_db()
    assert a1.valid_until is None


def test_dedupe_command_dry_run_then_apply(without_open_constraint, org_user, other_user, plant):
    _assign(org_user, scope_id=plant.id, valid_from=timezone.localdate() - timedelta(days=5))
    _assign(org_user, scope_id=plant.id)

    out = StringIO()
    call_command("dedupe_role_assignments", stdout=out)
    assert "DRY-RUN" in out.getvalue()
    assert "plant DUP" in out.getvalue()
    assert "dup@test.com" not in out.getvalue()
    assert RoleAssignment.objects.filter(scope_id=plant.id).count() == 2

    out = StringIO()
    call_command("dedupe_role_assignments", apply=True, user=org_user.email, stdout=out)
    assert "Rimosse 1" in out.getvalue()
    assert RoleAssignment.objects.filter(scope_id=plant.id).count() == 1

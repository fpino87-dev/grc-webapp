"""Test services governance — ruoli, successione, scadenze."""
import pytest
from datetime import date, timedelta
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="gov_svc", email="govsvc@test.com", password="test")


@pytest.fixture
def user2(db):
    return User.objects.create_user(username="gov_svc2", email="govsvc2@test.com", password="test")


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="GOV-P", name="Plant GOV", country="IT", nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def role_assignment(db, user):
    from apps.governance.models import RoleAssignment, NormativeRole
    return RoleAssignment.objects.create(
        user=user,
        role=NormativeRole.CISO,
        scope_type="org",
        valid_from=date.today(),
    )


# ── RoleAssignment.is_active ──────────────────────────────────────────────

@pytest.mark.django_db
def test_role_assignment_is_active_no_end(role_assignment):
    assert role_assignment.is_active is True


@pytest.mark.django_db
def test_role_assignment_is_active_with_future_end(user):
    from apps.governance.models import RoleAssignment, NormativeRole
    ra = RoleAssignment.objects.create(
        user=user, role=NormativeRole.DPO, scope_type="org",
        valid_from=date.today(),
        valid_until=date.today() + timedelta(days=30),
    )
    assert ra.is_active is True


@pytest.mark.django_db
def test_role_assignment_is_inactive_when_expired(user):
    from apps.governance.models import RoleAssignment, NormativeRole
    ra = RoleAssignment.objects.create(
        user=user, role=NormativeRole.RISK_MANAGER, scope_type="org",
        valid_from=date.today() - timedelta(days=60),
        valid_until=date.today() - timedelta(days=1),
    )
    assert ra.is_active is False


@pytest.mark.django_db
def test_role_assignment_is_inactive_when_future(user):
    from apps.governance.models import RoleAssignment, NormativeRole
    ra = RoleAssignment.objects.create(
        user=user, role=NormativeRole.INTERNAL_AUDITOR, scope_type="org",
        valid_from=date.today() + timedelta(days=10),
    )
    assert ra.is_active is False


# ── terminate_role service ────────────────────────────────────────────────

@pytest.mark.django_db
def test_terminate_role_sets_valid_until(role_assignment, user):
    from apps.governance.services import terminate_role
    yesterday = date.today() - timedelta(days=1)
    terminate_role(role_assignment, user, termination_date=yesterday, reason="Dimissioni")
    role_assignment.refresh_from_db()
    assert role_assignment.valid_until == yesterday
    assert role_assignment.is_active is False


# ── get_expiring_roles service ────────────────────────────────────────────

@pytest.mark.django_db
def test_get_expiring_roles_found(user):
    from apps.governance.models import RoleAssignment, NormativeRole
    from apps.governance.services import get_expiring_roles
    ra = RoleAssignment.objects.create(
        user=user, role=NormativeRole.CISO, scope_type="org",
        valid_from=date.today(),
        valid_until=date.today() + timedelta(days=10),
    )
    result = get_expiring_roles(days=30)
    expiring_ids = [str(r.id) for r in result["expiring"]]
    assert str(ra.id) in expiring_ids


@pytest.mark.django_db
def test_get_expiring_roles_excludes_far_future(user):
    from apps.governance.models import RoleAssignment, NormativeRole
    from apps.governance.services import get_expiring_roles
    ra = RoleAssignment.objects.create(
        user=user, role=NormativeRole.COMPLIANCE_OFFICER, scope_type="org",
        valid_from=date.today(),
        valid_until=date.today() + timedelta(days=365),
    )
    result = get_expiring_roles(days=30)
    # Returns dict with "expiring" and "expired" querysets
    expiring_ids = [str(r.id) for r in result["expiring"]]
    # Far-future expiry (365 days) should NOT be in the 30-day window
    assert str(ra.id) not in expiring_ids

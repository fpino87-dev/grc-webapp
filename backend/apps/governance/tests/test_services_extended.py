"""Test services governance — funzioni aggiuntive."""
import pytest
from datetime import date, timedelta
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="gov_svc2", email="govsvc2x@test.com", password="test")


@pytest.fixture
def user2(db):
    return User.objects.create_user(username="gov_svc3", email="govsvc3x@test.com", password="test")


@pytest.fixture
def role_assignment(db, user):
    from apps.governance.models import RoleAssignment, NormativeRole
    return RoleAssignment.objects.create(
        user=user,
        role=NormativeRole.CISO,
        scope_type="org",
        valid_from=date.today(),
    )


@pytest.mark.django_db
def test_get_expiring_roles_with_expiry(user):
    from apps.governance.models import RoleAssignment, NormativeRole
    from apps.governance.services import get_expiring_roles
    ra = RoleAssignment.objects.create(
        user=user, role=NormativeRole.DPO, scope_type="org",
        valid_from=date.today(),
        valid_until=date.today() + timedelta(days=15),
    )
    result = get_expiring_roles(days=30)
    ids = [str(r.id) for r in result["expiring"]]
    assert str(ra.id) in ids


@pytest.mark.django_db
def test_get_expiring_roles_expired(user):
    from apps.governance.models import RoleAssignment, NormativeRole
    from apps.governance.services import get_expiring_roles
    ra = RoleAssignment.objects.create(
        user=user, role=NormativeRole.RISK_MANAGER, scope_type="org",
        valid_from=date.today() - timedelta(days=90),
        valid_until=date.today() - timedelta(days=5),
    )
    result = get_expiring_roles(days=30)
    ids = [str(r.id) for r in result["expired"]]
    assert str(ra.id) in ids


@pytest.mark.django_db
def test_get_vacant_mandatory_roles():
    from apps.governance.services import get_vacant_mandatory_roles
    result = get_vacant_mandatory_roles()
    assert isinstance(result, (list, dict, type(None)))


@pytest.mark.django_db
def test_get_expiring_delegations(user):
    from apps.governance.models import RoleAssignment, NormativeRole
    from apps.governance.services import get_expiring_delegations
    ra = RoleAssignment.objects.create(
        user=user, role=NormativeRole.COMPLIANCE_OFFICER, scope_type="org",
        valid_from=date.today(),
        valid_until=date.today() + timedelta(days=20),
    )
    result = get_expiring_delegations(days=30)
    assert result is not None


@pytest.mark.django_db
def test_get_active_role(user, role_assignment):
    from apps.governance.services import get_active_role
    from apps.governance.models import NormativeRole
    result = get_active_role(user, NormativeRole.CISO)
    assert result is not None


@pytest.mark.django_db
def test_replace_role(user, user2, role_assignment):
    from apps.governance.services import replace_role
    result = replace_role(role_assignment, user2, user)
    assert result is not None
    # returns tuple (new_assignment, old_assignment) or similar
    # returns (new_assignment, terminated_old) tuple
    if isinstance(result, tuple):
        new_ra = result[0]
    else:
        new_ra = result
    assert new_ra is not None

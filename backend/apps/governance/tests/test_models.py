import pytest

from apps.governance.models import NormativeRole, RoleAssignment


@pytest.mark.django_db
def test_role_assignment_is_active_property():
    from django.contrib.auth import get_user_model
    from django.utils import timezone

    User = get_user_model()
    user = User.objects.create(username="u1")
    today = timezone.now().date()
    ra = RoleAssignment.objects.create(
        user=user,
        role=NormativeRole.CISO,
        scope_type="org",
        scope_id=None,
        valid_from=today,
    )
    assert ra.is_active is True


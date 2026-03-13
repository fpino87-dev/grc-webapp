import pytest

from apps.auth_grc.models import ExternalAuditorToken, GrcRole, UserPlantAccess


@pytest.mark.django_db
def test_external_auditor_token_lifecycle(plant_nis2, co_user):
    token_obj, raw = ExternalAuditorToken.create_token(
        user=co_user,
        plant=plant_nis2,
        framework_filter=[],
        valid_days=1,
        issued_by=co_user,
    )
    assert raw
    assert token_obj.is_valid
    token_obj.revoke()
    assert token_obj.is_valid is False


@pytest.mark.django_db
def test_user_plant_access_creation(plant_nis2, co_user):
    access = UserPlantAccess.objects.create(
        user=co_user,
        role=GrcRole.COMPLIANCE_OFFICER,
        scope_type="org",
    )
    assert access.pk


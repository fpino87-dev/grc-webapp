import pytest

from apps.plants.models import BusinessUnit, Plant


@pytest.mark.django_db
def test_plant_is_nis2_subject_flag():
    bu = BusinessUnit.objects.create(code="BU1", name="BU1")
    p = Plant.objects.create(
        code="P1",
        name="Plant 1",
        country="IT",
        bu=bu,
        nis2_scope="essenziale",
        status="attivo",
    )
    assert p.is_nis2_subject is True


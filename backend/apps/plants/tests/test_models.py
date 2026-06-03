import pytest
from django.core.exceptions import ValidationError

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


@pytest.mark.django_db
@pytest.mark.parametrize(
    "scope,expected",
    [("essenziale", True), ("importante", True), ("non_soggetto", False)],
)
def test_plant_is_nis2_subject_for_all_scopes(scope, expected):
    p = Plant.objects.create(
        code=f"P-{scope}", name="P", country="IT",
        nis2_scope=scope, status="attivo",
    )
    assert p.is_nis2_subject is expected


@pytest.mark.django_db
def test_plant_clean_allows_one_level_nesting():
    parent = Plant.objects.create(
        code="PARENT", name="Parent", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )
    child = Plant.objects.create(
        code="CHILD", name="Child", country="IT",
        nis2_scope="non_soggetto", status="attivo", parent_plant=parent,
    )
    child.clean()  # 1 livello: ok


@pytest.mark.django_db
def test_plant_clean_rejects_two_level_nesting():
    parent = Plant.objects.create(
        code="PARENT2", name="Parent", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )
    child = Plant.objects.create(
        code="CHILD2", name="Child", country="IT",
        nis2_scope="non_soggetto", status="attivo", parent_plant=parent,
    )
    grandchild = Plant(
        code="GC", name="GrandChild", country="IT",
        nis2_scope="non_soggetto", status="attivo", parent_plant=child,
    )
    with pytest.raises(ValidationError):
        grandchild.clean()


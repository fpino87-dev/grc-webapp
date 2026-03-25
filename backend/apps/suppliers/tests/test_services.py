"""Test services fornitori."""
import pytest
from datetime import date, timedelta
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="sup_svc", email="supsvc@test.com", password="test")


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="SPS-P", name="Plant SPS", country="IT", nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def supplier(db, plant, user):
    from apps.suppliers.models import Supplier
    s = Supplier.objects.create(name="Forn SVC", risk_level="medio", status="attivo", created_by=user)
    s.plants.add(plant)
    return s


# ── get_expiring_contracts ────────────────────────────────────────────────

@pytest.mark.django_db
def test_expiring_contracts_found(plant, user):
    from apps.suppliers.models import Supplier
    from apps.suppliers.services import get_expiring_contracts
    soon = date.today() + timedelta(days=30)
    s = Supplier.objects.create(name="Scade presto", risk_level="basso", status="attivo",
                                contract_expiry=soon, created_by=user)
    s.plants.add(plant)
    result = list(get_expiring_contracts(days=60))
    ids = [str(r.id) for r in result]
    assert str(s.id) in ids


@pytest.mark.django_db
def test_expiring_contracts_not_returned_if_expired(plant, user):
    from apps.suppliers.models import Supplier
    from apps.suppliers.services import get_expiring_contracts
    expired = date.today() - timedelta(days=1)
    s = Supplier.objects.create(name="Già scaduto", risk_level="basso", status="attivo",
                                contract_expiry=expired, created_by=user)
    s.plants.add(plant)
    result = list(get_expiring_contracts(days=60))
    ids = [str(r.id) for r in result]
    assert str(s.id) not in ids


@pytest.mark.django_db
def test_expiring_contracts_not_returned_if_terminated(plant, user):
    from apps.suppliers.models import Supplier
    from apps.suppliers.services import get_expiring_contracts
    soon = date.today() + timedelta(days=10)
    s = Supplier.objects.create(name="Terminato", risk_level="basso", status="terminato",
                                contract_expiry=soon, created_by=user)
    result = list(get_expiring_contracts(days=60))
    ids = [str(r.id) for r in result]
    assert str(s.id) not in ids


# ── get_high_risk_suppliers ───────────────────────────────────────────────

@pytest.mark.django_db
def test_high_risk_suppliers(plant, user):
    from apps.suppliers.models import Supplier
    from apps.suppliers.services import get_high_risk_suppliers
    s_alto = Supplier.objects.create(name="Alto", risk_level="alto", status="attivo", created_by=user)
    s_crit = Supplier.objects.create(name="Critico", risk_level="critico", status="attivo", created_by=user)
    s_basso = Supplier.objects.create(name="Basso", risk_level="basso", status="attivo", created_by=user)
    result = list(get_high_risk_suppliers())
    ids = [str(r.id) for r in result]
    assert str(s_alto.id) in ids
    assert str(s_crit.id) in ids
    assert str(s_basso.id) not in ids


# ── SupplierAssessment.computed_risk_level ────────────────────────────────

@pytest.mark.django_db
def test_computed_risk_level_verde(supplier, user):
    from apps.suppliers.models import SupplierAssessment
    a = SupplierAssessment.objects.create(supplier=supplier, assessed_by=user, status="completato",
                                          assessment_date=date.today(),
                                          score_overall=85, score=85, created_by=user)
    assert a.computed_risk_level == "verde"


@pytest.mark.django_db
def test_computed_risk_level_giallo(supplier, user):
    from apps.suppliers.models import SupplierAssessment
    a = SupplierAssessment.objects.create(supplier=supplier, assessed_by=user, status="completato",
                                          assessment_date=date.today(),
                                          score_overall=65, score=65, created_by=user)
    assert a.computed_risk_level == "giallo"


@pytest.mark.django_db
def test_computed_risk_level_rosso(supplier, user):
    from apps.suppliers.models import SupplierAssessment
    a = SupplierAssessment.objects.create(supplier=supplier, assessed_by=user, status="completato",
                                          assessment_date=date.today(),
                                          score_overall=40, score=40, created_by=user)
    assert a.computed_risk_level == "rosso"


@pytest.mark.django_db
def test_computed_risk_level_nd_when_no_score(supplier, user):
    from apps.suppliers.models import SupplierAssessment
    a = SupplierAssessment.objects.create(supplier=supplier, assessed_by=user, status="pianificato",
                                          assessment_date=date.today(), created_by=user)
    assert a.computed_risk_level == "nd"

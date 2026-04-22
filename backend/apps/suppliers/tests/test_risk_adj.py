"""Test risk_adj — Fase 3 (worst-case + bump NIS2)."""
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.suppliers.models import (
    Supplier,
    SupplierAssessment,
    SupplierEvaluationConfig,
)
from apps.suppliers.risk_adj import recompute_risk_adj, recompute_expired_risk_adj
from apps.suppliers.services import create_internal_evaluation

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="ra_user", email="ra@test.com", password="x")


@pytest.fixture
def supplier(db, user):
    return Supplier.objects.create(
        name="Risk Adj Co", vat_number="11223344556", created_by=user
    )


@pytest.fixture
def config(db):
    return SupplierEvaluationConfig.get_solo()


def _eval(supplier, user, level):
    """Helper: crea una valutazione interna che produce risk_class desiderata.
    level ∈ {1..5} — stesso score su tutti e 6 i parametri."""
    scores = {k: level for k in ("impatto", "accesso", "dati", "dipendenza", "integrazione", "compliance")}
    return create_internal_evaluation(supplier, scores, user)


def _approved_assessment(supplier, user, score_overall, assessment_date=None):
    assessment_date = assessment_date or timezone.now().date()
    return SupplierAssessment.objects.create(
        supplier=supplier,
        assessed_by=user,
        assessment_date=assessment_date,
        status="approvato",
        score_overall=score_overall,
        score=score_overall,
        reviewed_by=user,
        reviewed_at=timezone.now(),
        created_by=user,
    )


# ── Nessun dato → risk_adj vuoto ─────────────────────────────────────────

@pytest.mark.django_db
def test_no_internal_no_external_produces_empty_risk_adj(supplier):
    recompute_risk_adj(supplier)
    supplier.refresh_from_db()
    assert supplier.internal_risk_level == ""
    assert supplier.risk_adj == ""


# ── Solo interno ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_internal_only_sets_risk_adj(supplier, user):
    _eval(supplier, user, 1)  # tutto 1 → basso
    supplier.refresh_from_db()
    assert supplier.internal_risk_level == "basso"
    assert supplier.risk_adj == "basso"


# ── Solo esterno ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_external_only_within_validity(supplier, user):
    _approved_assessment(supplier, user, score_overall=80)  # >=75 → basso
    recompute_risk_adj(supplier)
    supplier.refresh_from_db()
    assert supplier.internal_risk_level == ""
    assert supplier.risk_adj == "basso"


@pytest.mark.django_db
def test_external_expired_does_not_contribute(supplier, user, config):
    old_date = timezone.now().date() - datetime.timedelta(days=config.assessment_validity_months * 30 + 10)
    _approved_assessment(supplier, user, score_overall=10, assessment_date=old_date)
    recompute_risk_adj(supplier)
    supplier.refresh_from_db()
    assert supplier.risk_adj == ""  # scaduto → non contribuisce, niente interno → vuoto


# ── Worst-case (max) ─────────────────────────────────────────────────────

@pytest.mark.django_db
def test_worst_case_external_higher(supplier, user):
    _eval(supplier, user, 1)  # interno basso
    _approved_assessment(supplier, user, score_overall=10)  # esterno critico
    recompute_risk_adj(supplier)
    supplier.refresh_from_db()
    assert supplier.internal_risk_level == "basso"
    assert supplier.risk_adj == "critico"  # worst-case vince


@pytest.mark.django_db
def test_worst_case_internal_higher(supplier, user):
    _eval(supplier, user, 5)  # interno critico
    _approved_assessment(supplier, user, score_overall=90)  # esterno basso
    recompute_risk_adj(supplier)
    supplier.refresh_from_db()
    assert supplier.internal_risk_level == "critico"
    assert supplier.risk_adj == "critico"


# ── Bump NIS2 + concentrazione ───────────────────────────────────────────

@pytest.mark.django_db
def test_bump_nis2_critical_concentration(supplier, user):
    supplier.nis2_relevant = True
    supplier.nis2_relevance_criterion = "ict"
    supplier.supply_concentration_pct = 60  # critica (>50%)
    supplier.save()
    _eval(supplier, user, 2)  # medio
    supplier.refresh_from_db()
    # medio + bump = alto
    assert supplier.internal_risk_level == "medio"
    assert supplier.risk_adj == "alto"


@pytest.mark.django_db
def test_bump_not_applied_if_concentration_not_critical(supplier, user):
    supplier.nis2_relevant = True
    supplier.nis2_relevance_criterion = "ict"
    supplier.supply_concentration_pct = 30  # media, non critica
    supplier.save()
    _eval(supplier, user, 2)  # medio
    supplier.refresh_from_db()
    assert supplier.risk_adj == "medio"  # niente bump


@pytest.mark.django_db
def test_bump_not_applied_if_not_nis2(supplier, user):
    supplier.nis2_relevant = False
    supplier.supply_concentration_pct = 80  # critica ma non NIS2
    supplier.save()
    _eval(supplier, user, 2)
    supplier.refresh_from_db()
    assert supplier.risk_adj == "medio"


@pytest.mark.django_db
def test_bump_config_disabled(supplier, user, config):
    config.nis2_concentration_bump = False
    config.save()
    supplier.nis2_relevant = True
    supplier.nis2_relevance_criterion = "ict"
    supplier.supply_concentration_pct = 70
    supplier.save()
    _eval(supplier, user, 2)
    supplier.refresh_from_db()
    assert supplier.risk_adj == "medio"  # bump disabilitato


@pytest.mark.django_db
def test_bump_saturates_at_critico(supplier, user):
    supplier.nis2_relevant = True
    supplier.nis2_relevance_criterion = "ict"
    supplier.supply_concentration_pct = 80
    supplier.save()
    _eval(supplier, user, 5)  # critico
    supplier.refresh_from_db()
    # critico + bump = critico (saturazione)
    assert supplier.risk_adj == "critico"


# ── Signal: cambio NIS2/concentrazione triggera ricalcolo ────────────────

@pytest.mark.django_db
def test_signal_recomputes_on_nis2_change(supplier, user):
    _eval(supplier, user, 2)
    supplier.refresh_from_db()
    assert supplier.risk_adj == "medio"

    supplier.nis2_relevant = True
    supplier.nis2_relevance_criterion = "ict"
    supplier.supply_concentration_pct = 80  # critica
    supplier.save()
    supplier.refresh_from_db()
    assert supplier.risk_adj == "alto"  # bump applicato automaticamente


# ── Hook approve_assessment ──────────────────────────────────────────────

@pytest.mark.django_db
def test_approve_assessment_triggers_recompute(supplier, user):
    from apps.suppliers.services import approve_assessment

    _eval(supplier, user, 1)  # interno basso
    assessment = SupplierAssessment.objects.create(
        supplier=supplier,
        assessed_by=user,
        assessment_date=timezone.now().date(),
        status="completato",
        score_overall=10,  # → critico
        score=10,
        created_by=user,
    )
    approve_assessment(assessment, user, notes="approvato per test")
    supplier.refresh_from_db()
    assert supplier.risk_adj == "critico"


# ── Task nightly ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_recompute_expired_risk_adj_runs_without_error(supplier, user):
    _eval(supplier, user, 3)
    count = recompute_expired_risk_adj()
    # Non deve sollevare; il conteggio dipende dallo stato pre-esistente
    assert count >= 0

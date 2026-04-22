"""Test SupplierInternalEvaluation model + service (Fase 2)."""
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.suppliers.models import (
    Supplier,
    SupplierEvaluationConfig,
    SupplierInternalEvaluation,
)
from apps.suppliers.services import create_internal_evaluation, _compute_weighted_score

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="ev_user", email="ev@test.com", password="x")


@pytest.fixture
def supplier(db, user):
    return Supplier.objects.create(
        name="Fornitore IE", vat_number="01234567890", risk_level="medio", created_by=user
    )


@pytest.fixture
def config(db):
    return SupplierEvaluationConfig.get_solo()


# ── Service ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_compute_weighted_score_with_default_weights(config):
    scores = {"impatto": 5, "accesso": 5, "dati": 5, "dipendenza": 5, "integrazione": 5, "compliance": 5}
    result = _compute_weighted_score(scores, config.weights)
    assert result == 5.0  # tutti i pesi sommano a 1, score uniforme = punteggio uniforme

    scores = {"impatto": 1, "accesso": 1, "dati": 1, "dipendenza": 1, "integrazione": 1, "compliance": 1}
    result = _compute_weighted_score(scores, config.weights)
    assert result == 1.0


@pytest.mark.django_db
def test_compute_weighted_score_mixed(config):
    # impatto=5 (peso 0.30) + altri=1 → 5*0.30 + 1*0.70 = 1.5 + 0.7 = 2.2
    scores = {"impatto": 5, "accesso": 1, "dati": 1, "dipendenza": 1, "integrazione": 1, "compliance": 1}
    result = _compute_weighted_score(scores, config.weights)
    assert result == 2.2


@pytest.mark.django_db
def test_create_internal_evaluation_basic(supplier, user):
    scores = {"impatto": 3, "accesso": 3, "dati": 3, "dipendenza": 3, "integrazione": 3, "compliance": 3}
    ev = create_internal_evaluation(supplier, scores, user, notes="prima valutazione")

    assert ev.score_impatto == 3
    assert float(ev.weighted_score) == 3.0
    assert ev.risk_class == "alto"  # 3.0 >= soglia alto (3.0)
    assert ev.is_current is True
    assert ev.evaluated_by == user
    assert ev.notes == "prima valutazione"
    assert ev.weights_snapshot  # snapshot pesi presente
    assert ev.thresholds_snapshot


@pytest.mark.django_db
def test_create_evaluation_invalid_score_range(supplier, user):
    bad = {"impatto": 6, "accesso": 3, "dati": 3, "dipendenza": 3, "integrazione": 3, "compliance": 3}
    with pytest.raises(ValidationError):
        create_internal_evaluation(supplier, bad, user)

    bad = {"impatto": 0, "accesso": 3, "dati": 3, "dipendenza": 3, "integrazione": 3, "compliance": 3}
    with pytest.raises(ValidationError):
        create_internal_evaluation(supplier, bad, user)


@pytest.mark.django_db
def test_create_evaluation_missing_score(supplier, user):
    incomplete = {"impatto": 3, "accesso": 3}
    with pytest.raises(ValidationError):
        create_internal_evaluation(supplier, incomplete, user)


@pytest.mark.django_db
def test_create_evaluation_marks_previous_not_current(supplier, user):
    scores1 = {"impatto": 1, "accesso": 1, "dati": 1, "dipendenza": 1, "integrazione": 1, "compliance": 1}
    ev1 = create_internal_evaluation(supplier, scores1, user)
    assert ev1.is_current is True

    scores2 = {"impatto": 5, "accesso": 5, "dati": 5, "dipendenza": 5, "integrazione": 5, "compliance": 5}
    ev2 = create_internal_evaluation(supplier, scores2, user)
    ev1.refresh_from_db()

    assert ev1.is_current is False
    assert ev2.is_current is True
    # Solo una "current" per fornitore
    current_count = SupplierInternalEvaluation.objects.filter(
        supplier=supplier, is_current=True
    ).count()
    assert current_count == 1
    # Storico mantenuto
    total = SupplierInternalEvaluation.objects.filter(supplier=supplier).count()
    assert total == 2


@pytest.mark.django_db
def test_classify_basso(supplier, user):
    # tutti 1 → 1.0 → basso
    scores = {k: 1 for k in ["impatto", "accesso", "dati", "dipendenza", "integrazione", "compliance"]}
    ev = create_internal_evaluation(supplier, scores, user)
    assert ev.risk_class == "basso"


@pytest.mark.django_db
def test_classify_critico(supplier, user):
    # tutti 5 → 5.0 → critico
    scores = {k: 5 for k in ["impatto", "accesso", "dati", "dipendenza", "integrazione", "compliance"]}
    ev = create_internal_evaluation(supplier, scores, user)
    assert ev.risk_class == "critico"


@pytest.mark.django_db
def test_audit_log_emitted(supplier, user):
    from core.audit import AuditLog
    count_before = AuditLog.objects.filter(action_code="suppliers.internal_evaluation.create").count()
    scores = {k: 3 for k in ["impatto", "accesso", "dati", "dipendenza", "integrazione", "compliance"]}
    create_internal_evaluation(supplier, scores, user)
    count_after = AuditLog.objects.filter(action_code="suppliers.internal_evaluation.create").count()
    assert count_after == count_before + 1


@pytest.mark.django_db
def test_snapshot_preserves_weights_at_evaluation_time(supplier, user, config):
    """Se i pesi cambiano dopo, le valutazioni storiche conservano i pesi originari."""
    scores = {k: 3 for k in ["impatto", "accesso", "dati", "dipendenza", "integrazione", "compliance"]}
    ev1 = create_internal_evaluation(supplier, scores, user)
    original_weights = dict(ev1.weights_snapshot)

    # Cambia pesi
    config.weights = {"impatto": 0.50, "accesso": 0.10, "dati": 0.10, "dipendenza": 0.10, "integrazione": 0.10, "compliance": 0.10}
    config.save()

    ev2 = create_internal_evaluation(supplier, scores, user)
    ev1.refresh_from_db()
    assert ev1.weights_snapshot == original_weights  # storico immutato
    assert ev2.weights_snapshot["impatto"] == 0.50  # nuova ha pesi correnti

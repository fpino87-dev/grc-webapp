"""Test risk_adj — Fase 3 (worst-case + bump NIS2).

Sorgenti di rischio (tutte opzionali, worst-case):
  1. Valutazione interna: SupplierInternalEvaluation (is_current=True)
  2. Questionario:        SupplierQuestionnaire (status='risposto', expires_at >= oggi)
  3. Audit terze parti:   SupplierAssessment (status='approvato', entro validità config)
"""
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.suppliers.models import (
    Supplier,
    SupplierAssessment,
    SupplierEvaluationConfig,
    SupplierQuestionnaire,
    QuestionnaireTemplate,
)
from apps.suppliers.risk_adj import recompute_risk_adj, recompute_expired_risk_adj
from apps.suppliers.services import (
    approve_assessment,
    create_internal_evaluation,
    register_evaluation,
)

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


@pytest.fixture
def template(db, user):
    return QuestionnaireTemplate.objects.create(
        name="T1",
        subject="Test",
        body="Body",
        form_url="https://example.com/form",
        created_by=user,
    )


def _eval(supplier, user, level):
    """Helper: crea una valutazione interna con risk_class basata su level (1–5)."""
    scores = {k: level for k in ("impatto", "accesso", "dati", "dipendenza", "integrazione", "compliance")}
    return create_internal_evaluation(supplier, scores, user)


def _questionnaire(supplier, user, template, risk_result, evaluation_date=None, expired=False):
    """Helper: crea un questionario risposto con risk_result desiderato."""
    evaluation_date = evaluation_date or timezone.now().date()
    if expired:
        expires_at = evaluation_date - datetime.timedelta(days=1)
    else:
        expires_at = evaluation_date + datetime.timedelta(days=365)
    return SupplierQuestionnaire.objects.create(
        supplier=supplier,
        template=template,
        subject_snapshot="Test",
        body_snapshot="Body",
        form_url_snapshot="https://example.com/form",
        sent_at=timezone.now(),
        last_sent_at=timezone.now(),
        sent_to=supplier.email or "test@example.com",
        sent_by=user,
        send_count=1,
        status="risposto",
        evaluation_date=evaluation_date,
        risk_result=risk_result,
        expires_at=expires_at,
        created_by=user,
    )


# ── Nessun dato → risk_adj vuoto ─────────────────────────────────────────

@pytest.mark.django_db
def test_no_internal_no_questionnaire_produces_empty_risk_adj(supplier):
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


# ── Solo questionario ─────────────────────────────────────────────────────

@pytest.mark.django_db
def test_questionnaire_only_within_validity(supplier, user, template):
    _questionnaire(supplier, user, template, risk_result="basso")
    recompute_risk_adj(supplier)
    supplier.refresh_from_db()
    assert supplier.internal_risk_level == ""
    assert supplier.risk_adj == "basso"


@pytest.mark.django_db
def test_questionnaire_expired_does_not_contribute(supplier, user, template):
    _questionnaire(supplier, user, template, risk_result="critico", expired=True)
    recompute_risk_adj(supplier)
    supplier.refresh_from_db()
    assert supplier.risk_adj == ""  # scaduto → non contribuisce


# ── Worst-case (max) ─────────────────────────────────────────────────────

@pytest.mark.django_db
def test_worst_case_questionnaire_higher(supplier, user, template):
    _eval(supplier, user, 1)  # interno basso
    _questionnaire(supplier, user, template, risk_result="critico")
    recompute_risk_adj(supplier)
    supplier.refresh_from_db()
    assert supplier.internal_risk_level == "basso"
    assert supplier.risk_adj == "critico"  # worst-case vince


@pytest.mark.django_db
def test_worst_case_internal_higher(supplier, user, template):
    _eval(supplier, user, 5)  # interno critico
    _questionnaire(supplier, user, template, risk_result="basso")
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


# ── Hook register_evaluation triggera ricalcolo ──────────────────────────

@pytest.mark.django_db
def test_register_evaluation_triggers_recompute(supplier, user, template):
    _eval(supplier, user, 1)  # interno basso
    q = SupplierQuestionnaire.objects.create(
        supplier=supplier,
        template=template,
        subject_snapshot="Test",
        body_snapshot="Body",
        form_url_snapshot="https://example.com/form",
        sent_at=timezone.now(),
        last_sent_at=timezone.now(),
        sent_to="test@example.com",
        sent_by=user,
        send_count=1,
        status="inviato",
        created_by=user,
    )
    register_evaluation(q, timezone.now().date(), "critico", user)
    supplier.refresh_from_db()
    assert supplier.risk_adj == "critico"


# ── Audit terze parti (SupplierAssessment approvato) ─────────────────────

def _approved_assessment(supplier, user, score_overall, assessment_date=None):
    return SupplierAssessment.objects.create(
        supplier=supplier,
        assessed_by=user,
        assessment_date=assessment_date or timezone.now().date(),
        status="approvato",
        score_overall=score_overall,
        score=score_overall,
        reviewed_by=user,
        reviewed_at=timezone.now(),
        created_by=user,
    )


@pytest.mark.django_db
def test_audit_only_within_validity(supplier, user):
    _approved_assessment(supplier, user, score_overall=80)  # >=75 → basso
    recompute_risk_adj(supplier)
    supplier.refresh_from_db()
    assert supplier.internal_risk_level == ""
    assert supplier.risk_adj == "basso"


@pytest.mark.django_db
def test_audit_expired_does_not_contribute(supplier, user, config):
    old_date = timezone.now().date() - datetime.timedelta(days=config.assessment_validity_months * 30 + 10)
    _approved_assessment(supplier, user, score_overall=10, assessment_date=old_date)
    recompute_risk_adj(supplier)
    supplier.refresh_from_db()
    assert supplier.risk_adj == ""  # scaduto → non partecipa


@pytest.mark.django_db
def test_worst_case_three_sources(supplier, user, template):
    _eval(supplier, user, 1)                                    # interno → basso
    _questionnaire(supplier, user, template, risk_result="medio")  # questionario → medio
    _approved_assessment(supplier, user, score_overall=10)      # audit → critico
    recompute_risk_adj(supplier)
    supplier.refresh_from_db()
    assert supplier.risk_adj == "critico"  # audit vince


@pytest.mark.django_db
def test_worst_case_questionnaire_beats_audit(supplier, user, template):
    _eval(supplier, user, 1)                                      # interno → basso
    _questionnaire(supplier, user, template, risk_result="critico")  # questionario → critico
    _approved_assessment(supplier, user, score_overall=80)        # audit → basso
    recompute_risk_adj(supplier)
    supplier.refresh_from_db()
    assert supplier.risk_adj == "critico"  # questionario vince


@pytest.mark.django_db
def test_approve_assessment_triggers_recompute(supplier, user):
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


@pytest.mark.django_db
def test_soft_delete_assessment_triggers_recompute(supplier, user):
    _eval(supplier, user, 1)  # interno basso
    assessment = _approved_assessment(supplier, user, score_overall=10)  # audit critico
    recompute_risk_adj(supplier)
    supplier.refresh_from_db()
    assert supplier.risk_adj == "critico"

    # Elimina l'audit → risk_adj torna al solo interno
    assessment.soft_delete()
    recompute_risk_adj(supplier)
    supplier.refresh_from_db()
    assert supplier.risk_adj == "basso"


# ── Task nightly ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_recompute_expired_risk_adj_runs_without_error(supplier, user):
    _eval(supplier, user, 3)
    count = recompute_expired_risk_adj()
    assert count >= 0

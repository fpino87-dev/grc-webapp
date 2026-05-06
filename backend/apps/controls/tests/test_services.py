"""
Test services controls: evaluate_control, validate_exclusion, get_compliance_summary.
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def user(db):
    return User.objects.create_user(username="ctrl@test.com", email="ctrl@test.com", password="x")


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="CTRL-P", name="Plant Ctrl", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def framework(db):
    from apps.controls.models import Framework
    return Framework.objects.create(
        code="ISO27K", name="ISO 27001", version="2022", published_at="2022-10-01"
    )


@pytest.fixture
def control_no_req(db, framework):
    """Controllo senza evidence_requirement."""
    from apps.controls.models import Control
    return Control.objects.create(
        framework=framework,
        external_id="C-NO-REQ",
        translations={"it": {"title": "Controllo senza requisiti"}},
        evidence_requirement={},
    )


@pytest.fixture
def control_with_req(db, framework):
    """Controllo con evidence_requirement che richiede un documento."""
    from apps.controls.models import Control
    return Control.objects.create(
        framework=framework,
        external_id="C-WITH-REQ",
        translations={"it": {"title": "Controllo con requisiti"}},
        evidence_requirement={
            "min_evidences": 1,
            "evidences": [{"type": "assessment", "description": "Security assessment"}],
        },
    )


@pytest.fixture
def instance_no_req(db, plant, control_no_req):
    from apps.controls.models import ControlInstance
    return ControlInstance.objects.create(plant=plant, control=control_no_req)


@pytest.fixture
def instance_with_req(db, plant, control_with_req):
    from apps.controls.models import ControlInstance
    return ControlInstance.objects.create(plant=plant, control=control_with_req)


# ── evaluate_control ──────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_evaluate_control_gap_no_evidence_required(instance_no_req, user):
    """gap non richiede evidenze."""
    from apps.controls.services import evaluate_control
    result = evaluate_control(instance_no_req, "gap", user)
    assert result.status == "gap"


@pytest.mark.django_db
def test_evaluate_control_non_valutato(instance_no_req, user):
    from apps.controls.services import evaluate_control
    result = evaluate_control(instance_no_req, "non_valutato", user)
    assert result.status == "non_valutato"


@pytest.mark.django_db
def test_evaluate_control_compliant_without_evidence_raises(instance_with_req, user):
    """compliant con requisiti non soddisfatti → ValidationError."""
    from apps.controls.services import evaluate_control
    with pytest.raises(ValidationError):
        evaluate_control(instance_with_req, "compliant", user)


@pytest.mark.django_db
def test_evaluate_control_na_short_justification_raises(instance_no_req, user):
    """N/A con giustificazione < 20 caratteri → ValidationError."""
    from apps.controls.services import evaluate_control
    with pytest.raises(ValidationError):
        evaluate_control(instance_no_req, "na", user, note="troppo corta")


@pytest.mark.django_db
def test_evaluate_control_na_valid_justification(instance_no_req, user):
    """N/A con giustificazione ≥ 20 caratteri → OK."""
    from apps.controls.services import evaluate_control
    result = evaluate_control(
        instance_no_req, "na", user,
        note="Controllo non applicabile al contesto produttivo corrente."
    )
    assert result.status == "na"


@pytest.mark.django_db
def test_evaluate_control_parziale_without_evidence_raises(instance_no_req, user):
    """parziale senza documenti o evidenze → ValidationError."""
    from apps.controls.services import evaluate_control
    with pytest.raises(ValidationError):
        evaluate_control(instance_no_req, "parziale", user)


# ── validate_exclusion ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_validate_exclusion_short_justification_raises(instance_no_req, user):
    from apps.controls.services import validate_exclusion
    with pytest.raises(ValidationError):
        validate_exclusion(instance_no_req, "escluso", "troppo corta", user)


@pytest.mark.django_db
def test_validate_exclusion_sets_status_na(instance_no_req, user):
    from apps.controls.services import validate_exclusion
    justification = "Il controllo è formalmente escluso perché non applicabile al processo in esame per ragioni di compliance documentate."
    validate_exclusion(instance_no_req, "escluso", justification, user)
    instance_no_req.refresh_from_db()
    assert instance_no_req.status == "na"
    assert instance_no_req.applicability == "escluso"


@pytest.mark.django_db
def test_validate_exclusion_applicabile_no_justification_needed(instance_no_req, user):
    from apps.controls.services import validate_exclusion
    validate_exclusion(instance_no_req, "applicabile", "", user)
    instance_no_req.refresh_from_db()
    assert instance_no_req.applicability == "applicabile"


# ── get_compliance_summary ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_get_compliance_summary_counts(plant, framework, user):
    from apps.controls.models import Control, ControlInstance
    from apps.controls.services import evaluate_control, get_compliance_summary

    c1 = Control.objects.create(framework=framework, external_id="S1", translations={}, evidence_requirement={})
    c2 = Control.objects.create(framework=framework, external_id="S2", translations={}, evidence_requirement={})
    c3 = Control.objects.create(framework=framework, external_id="S3", translations={}, evidence_requirement={})

    i1 = ControlInstance.objects.create(plant=plant, control=c1)
    i2 = ControlInstance.objects.create(plant=plant, control=c2)
    i3 = ControlInstance.objects.create(plant=plant, control=c3)

    evaluate_control(i1, "gap", user)
    evaluate_control(i2, "gap", user)
    evaluate_control(
        i3, "na", user,
        note="Controllo non applicabile al contesto produttivo attuale."
    )

    summary = get_compliance_summary(str(plant.pk), framework_code="ISO27K")
    # Nuova semantica: N/A esclusi dal denominatore (vedono fuori contesto
    # organizzativo), riportati separatamente in `na_excluded`.
    assert summary["gap"] == 2
    assert summary["na_excluded"] == 1
    assert summary["total"] == 2  # solo i 2 gap, l'N/A non conta come applicabile
    assert summary["compliant"] == 0
    assert summary["covered_by_extender"] == 0
    assert summary["pct_compliant"] == 0

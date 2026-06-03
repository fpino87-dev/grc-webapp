"""Regression test atomicità (P1-2): le azioni multi-write del modulo risk
devono essere tutto-o-niente — un fallimento a metà non deve lasciare stato
parziale a DB né audit trail incoerente."""
from unittest import mock

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="risk_atom", email="riskatom@test.com", password="test")


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="RSK-ATOM", name="Plant Risk Atom", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def assessment(db, plant, user):
    from apps.risk.models import RiskAssessment
    return RiskAssessment.objects.create(
        plant=plant,
        name="Rischio Atomicità",
        assessment_type="IT",
        threat_category="malware_ransomware",
        probability=3,
        impact=4,
        created_by=user,
    )


@pytest.mark.django_db
def test_accept_risk_rolls_back_on_audit_failure(assessment, user):
    """Se l'audit log fallisce, l'accettazione formale non deve persistere."""
    from apps.risk.services import accept_risk

    with mock.patch("core.audit.log_action", side_effect=RuntimeError("audit down")):
        with pytest.raises(RuntimeError):
            accept_risk(assessment, user, note="Accettazione formale documentata per motivi aziendali")

    assessment.refresh_from_db()
    assert assessment.risk_accepted_formally is False
    assert assessment.risk_accepted is False
    assert assessment.risk_accepted_by_id is None


@pytest.mark.django_db
def test_accept_risk_validation(assessment, user):
    """Validazioni nota obbligatoria: nessuna scrittura se la nota non rispetta i vincoli."""
    from django.core.exceptions import ValidationError
    from apps.risk.services import accept_risk

    # Rischio non-rosso senza nota → errore
    with pytest.raises(ValidationError):
        accept_risk(assessment, user, note="")

    # Rischio rosso (score 5*4=20) con nota troppo corta → errore
    assessment.probability = 5
    assessment.impact = 4
    assessment.save()
    with pytest.raises(ValidationError):
        accept_risk(assessment, user, note="troppo corta")

    assessment.refresh_from_db()
    assert assessment.risk_accepted_formally is False


@pytest.mark.django_db
def test_delete_risk_assessment_rolls_back_on_failure(assessment, user):
    """Se il soft-delete dell'assessment fallisce dopo aver cancellato le dimensioni,
    le dimensioni devono restare integre (cascata tutto-o-niente)."""
    from apps.risk.models import RiskDimension
    from apps.risk.services import delete_risk_assessment

    dim = RiskDimension.objects.create(
        assessment=assessment, dimension_code="C", value=4, created_by=user,
    )

    with mock.patch.object(
        type(assessment), "soft_delete", autospec=True, side_effect=RuntimeError("boom"),
    ):
        with pytest.raises(RuntimeError):
            delete_risk_assessment(assessment, user)

    dim.refresh_from_db()
    assert dim.deleted_at is None, "la dimensione non deve risultare cancellata dopo il rollback"
    assessment.refresh_from_db()
    assert assessment.deleted_at is None


@pytest.mark.django_db
def test_escalate_red_risk_rolls_back_tasks_on_failure(assessment, user):
    """Se la creazione del secondo task (soglia CISO) fallisce, anche il primo task
    di mitigazione deve essere annullato."""
    from apps.risk.models import RiskAppetitePolicy
    from apps.tasks.models import Task

    # Appetite con soglia bassa e max_red_risks=0 → forza il secondo create_task (CISO).
    RiskAppetitePolicy.objects.create(
        plant=assessment.plant,
        framework_code="",
        max_acceptable_score=1,
        max_red_risks_count=0,
        valid_from=assessment.created_at.date(),
        created_by=user,
    )
    # save() ricalcola score = probability * impact → 5*4 = 20, sopra la soglia.
    assessment.probability = 5
    assessment.impact = 4
    assessment.save()

    from apps.risk import services as risk_services
    import apps.tasks.services as tasks_services

    real_create_task = tasks_services.create_task  # catturata prima della patch
    calls = {"n": 0}

    def flaky_create_task(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] >= 2:
            raise RuntimeError("task service down")
        return real_create_task(*args, **kwargs)

    with mock.patch("apps.tasks.services.create_task", side_effect=flaky_create_task):
        with pytest.raises(RuntimeError):
            risk_services.escalate_red_risk(assessment, user)

    assert Task.objects.filter(source_module="M06", source_id=assessment.pk).count() == 0, (
        "nessun task deve restare se la creazione a cascata fallisce"
    )


@pytest.mark.django_db
def test_escalate_red_risk_notifies_only_after_commit(assessment, user, django_capture_on_commit_callbacks):
    """Percorso felice: il task viene creato e la notifica email parte solo dopo
    il commit (schedulata via transaction.on_commit)."""
    from apps.risk.services import escalate_red_risk
    from apps.tasks.models import Task

    # save() ricalcola score = probability * impact → 5*4 = 20, sopra la soglia (14).
    assessment.probability = 5
    assessment.impact = 4
    assessment.save()

    with mock.patch("apps.notifications.resolver.fire_notification") as fire:
        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            escalate_red_risk(assessment, user)
        # il task esiste già a fine funzione, la notifica è solo schedulata
        assert Task.objects.filter(source_module="M06", source_id=assessment.pk).exists()
        assert len(callbacks) == 1
    fire.assert_called_once()


@pytest.mark.django_db
def test_escalate_red_risk_swallows_notification_error(assessment, user, django_capture_on_commit_callbacks):
    """La notifica email è best-effort: se fire_notification solleva nella callback
    on_commit, l'escalation (task già creati) non deve fallire."""
    from apps.risk.services import escalate_red_risk
    from apps.tasks.models import Task

    assessment.probability = 5
    assessment.impact = 4
    assessment.save()

    with mock.patch(
        "apps.notifications.resolver.fire_notification", side_effect=RuntimeError("smtp down")
    ):
        with django_capture_on_commit_callbacks(execute=True):
            escalate_red_risk(assessment, user)

    assert Task.objects.filter(source_module="M06", source_id=assessment.pk).exists()

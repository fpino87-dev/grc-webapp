"""
Degrado automatico per documento non più approvato e ripristino (M03/M07).

Un controllo Compliant scende a Parziale nel giro notturno se il documento
collegato è tornato in revisione. Quando il documento è di nuovo approvato lo
stato Compliant torna da solo — purché nel frattempo nessuno abbia rivalutato
il controllo e le evidenze siano ancora a posto.
"""
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="own@test.com", email="own@test.com", password="x")


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(username="sys@test.com", email="sys@test.com", password="x")


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="DEG-P", name="Plant Degrado", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def framework(db, plant):
    from apps.controls.models import Framework
    from apps.plants.models import PlantFramework
    fw = Framework.objects.create(
        code="ISO-DEG", name="ISO 27001", version="2022", published_at="2022-10-01"
    )
    PlantFramework.objects.create(plant=plant, framework=fw, active_from="2024-01-01")
    return fw


def _control(framework, external_id, requirement):
    from apps.controls.models import Control
    return Control.objects.create(
        framework=framework, external_id=external_id,
        translations={"it": {"title": external_id}},
        evidence_requirement=requirement,
    )


@pytest.fixture
def document(db, plant, user):
    from apps.documents.models import Document
    return Document.objects.create(
        title="Procedura accessi", category="procedura", document_type="procedura",
        status="approvato", plant=plant, created_by=user,
    )


@pytest.fixture
def instance(db, plant, framework, user, document):
    """Controllo Compliant che richiede un documento approvato."""
    from apps.controls.models import ControlInstance
    control = _control(framework, "A.5.15", {
        "documents": [{"type": "procedura", "mandatory": True}],
    })
    ci = ControlInstance.objects.create(
        plant=plant, control=control, owner=user, status="compliant",
        last_evaluated_at=timezone.now() - datetime.timedelta(days=30),
    )
    document.control_refs.add(ci)
    return ci


def _to_review(document):
    document.status = "revisione"
    document.save(update_fields=["status"])


def _run_nightly():
    from apps.controls.tasks import check_expired_evidences
    return check_expired_evidences()


def _open_tasks(instance):
    from apps.tasks.models import Task
    return Task.objects.filter(source_id=instance.pk, status__in=("aperto", "in_corso"))


def test_nightly_degrades_and_marks_document_cause(instance, document, superuser):
    from apps.controls.services import DOCUMENT_DEGRADED_TASK_PREFIX

    _to_review(document)
    _run_nightly()

    instance.refresh_from_db()
    assert instance.status == "parziale"
    assert instance.document_degraded_at is not None
    assert _open_tasks(instance).get().title.startswith(DOCUMENT_DEGRADED_TASK_PREFIX)


def test_approval_restores_compliant_and_closes_task(instance, document, superuser, user):
    from core.audit import AuditLog
    from apps.documents.services import approve_document

    evaluated_at = instance.last_evaluated_at
    _to_review(document)
    _run_nightly()

    approve_document(document, superuser, notes="ok")

    instance.refresh_from_db()
    assert instance.status == "compliant"
    assert instance.document_degraded_at is None
    # non è una nuova valutazione: resta valida quella precedente
    assert instance.last_evaluated_at == evaluated_at
    assert not _open_tasks(instance).exists()
    log = AuditLog.objects.get(
        action_code="control.restored_compliant", entity_id=instance.pk
    )
    assert log.payload["reason"] == "documents_approved_again"


def test_nightly_restores_when_requirements_met_by_other_means(instance, document, superuser):
    """Rete di sicurezza: requisiti tornati soddisfatti senza passare
    dall'approvazione (es. collegato un altro documento approvato)."""
    from apps.documents.models import Document

    _to_review(document)
    _run_nightly()
    other = Document.objects.create(
        title="Procedura sostitutiva", category="procedura", document_type="procedura",
        status="approvato", plant=instance.plant,
    )
    other.control_refs.add(instance)

    result = _run_nightly()

    instance.refresh_from_db()
    assert instance.status == "compliant"
    assert "1 ripristinati" in result


def test_no_restore_after_manual_evaluation(instance, document, superuser, user):
    """Chi rivaluta il controllo decide lo stato: nessun ripristino automatico."""
    from apps.controls.services import evaluate_control
    from apps.documents.services import approve_document

    _to_review(document)
    _run_nightly()
    instance.refresh_from_db()
    evaluate_control(instance, "gap", user, note="Procedura da riscrivere")

    approve_document(document, superuser, notes="ok")

    instance.refresh_from_db()
    assert instance.status == "gap"
    assert instance.document_degraded_at is None


def test_no_restore_while_another_requirement_is_unmet(instance, document, superuser, plant):
    """Documento riapprovato ma evidenza nel frattempo scaduta: resta Parziale."""
    from apps.documents.models import Evidence
    from apps.documents.services import approve_document

    today = timezone.localdate()
    instance.control.evidence_requirement = {
        "documents": [{"type": "procedura", "mandatory": True}],
        "evidences": [{"type": "report", "mandatory": True}],
    }
    instance.control.save(update_fields=["evidence_requirement"])
    evidence = Evidence.objects.create(
        title="Report accessi", evidence_type="report", plant=plant,
        valid_until=today + datetime.timedelta(days=10),
    )
    instance.evidences.add(evidence)

    _to_review(document)
    _run_nightly()
    instance.refresh_from_db()
    assert instance.document_degraded_at is not None

    evidence.valid_until = today - datetime.timedelta(days=1)
    evidence.save(update_fields=["valid_until"])
    approve_document(document, superuser, notes="ok")

    instance.refresh_from_db()
    assert instance.status == "parziale"


def test_evidence_expiry_is_not_auto_restored(plant, framework, user, superuser):
    """Il degrado per evidenza scaduta non è temporaneo: serve una rivalutazione."""
    from apps.controls.models import ControlInstance
    from apps.documents.models import Evidence

    today = timezone.localdate()
    control = _control(framework, "A.8.15", {
        "evidences": [{"type": "log", "mandatory": True}],
    })
    ci = ControlInstance.objects.create(plant=plant, control=control, owner=user, status="compliant")
    expired = Evidence.objects.create(
        title="Log vecchio", evidence_type="log", plant=plant,
        valid_until=today - datetime.timedelta(days=1),
    )
    ci.evidences.add(expired)

    _run_nightly()
    ci.refresh_from_db()
    assert ci.status == "parziale"
    assert ci.document_degraded_at is None

    fresh = Evidence.objects.create(
        title="Log nuovo", evidence_type="log", plant=plant,
        valid_until=today + datetime.timedelta(days=90),
    )
    ci.evidences.add(fresh)
    _run_nightly()

    ci.refresh_from_db()
    assert ci.status == "parziale"


def test_backfill_marks_controls_degraded_before_the_marker_existed(
    instance, document, superuser, user
):
    """Migrazione 0016: i controlli già degradati dal task notturno vengono
    segnati leggendo l'audit trail; quelli rivalutati dopo il degrado no."""
    import importlib

    from django.apps import apps as django_apps

    from apps.controls.models import ControlInstance
    from apps.controls.services import evaluate_control

    migration = importlib.import_module(
        "apps.controls.migrations.0016_backfill_document_degraded_at"
    )
    other_control = _control(instance.control.framework, "A.5.16", {
        "documents": [{"type": "procedura", "mandatory": True}],
    })
    evaluated_after = ControlInstance.objects.create(
        plant=instance.plant, control=other_control, owner=user, status="compliant",
    )
    document.control_refs.add(evaluated_after)

    _to_review(document)
    _run_nightly()
    # stato del database prima di questa modifica: degradati, senza segnale
    ControlInstance.objects.update(document_degraded_at=None)
    document.status = "approvato"
    document.save(update_fields=["status"])
    evaluated_after.refresh_from_db()
    evaluate_control(evaluated_after, "parziale", user, note="Procedura applicata solo in parte")

    migration.backfill(django_apps, None)

    instance.refresh_from_db()
    evaluated_after.refresh_from_db()
    assert instance.document_degraded_at is not None
    assert evaluated_after.document_degraded_at is None

    _run_nightly()
    instance.refresh_from_db()
    evaluated_after.refresh_from_db()
    assert instance.status == "compliant"
    assert evaluated_after.status == "parziale"

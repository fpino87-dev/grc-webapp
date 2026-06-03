"""P2-4 — catena PDCA↔finding automatico (bidirezionale).

Forward (già esistente): aprire un finding major/minor genera e collega un ciclo
PDCA. Reverse (P2-4): chiudere quel ciclo PDCA dal modulo M11 fa avanzare il
finding ancora aperto a `in_response` (azione correttiva completata), senza
chiuderlo formalmente.
"""
import datetime

import pytest
from django.contrib.auth import get_user_model

from apps.audit_prep.models import AuditFinding, AuditPrep
from apps.audit_prep.services import open_finding
from apps.pdca.services import close_cycle, create_cycle
from apps.plants.models import Plant

User = get_user_model()
pytestmark = pytest.mark.django_db

TODAY = datetime.date(2026, 5, 20)


@pytest.fixture
def user(db):
    return User.objects.create_user(username="auditor", email="a@t.com", password="x")


@pytest.fixture
def prep(db, user):
    plant = Plant.objects.create(
        code="FP-P", name="Plant FP", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )
    return AuditPrep.objects.create(plant=plant, title="Audit ISO 2026", created_by=user)


def _finding(prep, user, finding_type, title="Finding X"):
    return open_finding(
        audit_prep=prep, finding_type=finding_type, title=title,
        description="Descrizione del rilievo di audit.", audit_date=TODAY, user=user,
    )


def _close_linked_pdca(finding, user):
    cycle = finding.pdca_cycle
    cycle.fase_corrente = "act"
    cycle.save(update_fields=["fase_corrente"])
    return close_cycle(cycle, user, act_description="Azione standardizzata applicata e verificata.")


# ── forward: finding → PDCA ─────────────────────────────────────────────────


def test_open_major_creates_linked_pdca(prep, user):
    f = _finding(prep, user, "major_nc")
    assert f.pdca_cycle is not None
    assert f.pdca_cycle.trigger_type == "finding_major"
    assert f.pdca_cycle.scope_type == "finding"
    assert str(f.pdca_cycle.trigger_source_id) == str(f.pk)


def test_open_minor_creates_linked_pdca(prep, user):
    f = _finding(prep, user, "minor_nc")
    assert f.pdca_cycle is not None
    assert f.pdca_cycle.trigger_type == "finding_minor"


def test_open_observation_has_no_pdca(prep, user):
    f = _finding(prep, user, "observation")
    assert f.pdca_cycle is None


# ── reverse: PDCA chiuso → finding avanza ───────────────────────────────────


def test_close_pdca_advances_open_finding_to_in_response(prep, user):
    f = _finding(prep, user, "minor_nc")
    assert f.status == "open"
    _close_linked_pdca(f, user)
    f.refresh_from_db()
    assert f.status == "in_response"


def test_close_pdca_does_not_close_finding(prep, user):
    """Il finding NON viene chiuso dalla chiusura del PDCA (la chiusura formale
    richiede evidenza e passa da close_finding)."""
    f = _finding(prep, user, "major_nc")
    _close_linked_pdca(f, user)
    f.refresh_from_db()
    assert f.status != "closed"


def test_close_pdca_ignores_already_closed_finding(prep, user):
    """Guard: se il finding è già chiuso (path close_finding → close_cycle), la
    chiusura del ciclo non lo riporta a in_response."""
    f = _finding(prep, user, "minor_nc")
    f.status = "closed"
    f.save(update_fields=["status"])
    _close_linked_pdca(f, user)
    f.refresh_from_db()
    assert f.status == "closed"


def test_close_pdca_writes_finding_audit(prep, user):
    from core.audit import AuditLog

    f = _finding(prep, user, "minor_nc")
    _close_linked_pdca(f, user)
    assert AuditLog.objects.filter(
        action_code="audit.finding.pdca_closed", entity_id=f.pk
    ).exists()


def test_close_non_finding_cycle_no_side_effect(prep, user):
    """Un ciclo PDCA non legato a finding si chiude senza toccare i finding."""
    cycle = create_cycle(
        plant=prep.plant, title="Miglioramento custom", trigger_type="custom",
    )
    cycle.fase_corrente = "act"
    cycle.save(update_fields=["fase_corrente"])
    # Non solleva e non crea/altera finding
    close_cycle(cycle, user, act_description="Azione standardizzata applicata e verificata.")
    assert AuditFinding.objects.count() == 0

"""P2-1 — copertura management_review/services.py (complete, snapshot, approve)."""
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="mrs", email="mrs@x.it", password="x")


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="MRS-P", name="Plant MR", country="IT",
                                nis2_scope="essenziale", status="attivo")


@pytest.fixture
def review(db, plant, user):
    from apps.management_review.models import ManagementReview
    return ManagementReview.objects.create(
        plant=plant, title="Riesame 2026", review_date=timezone.localdate(),
        status="pianificato", created_by=user,
    )


def test_complete_review_snapshots_kpis(review, user):
    from apps.management_review.services import complete_review
    out = complete_review(review, user)
    out.refresh_from_db()
    assert out.status == "completato"
    # kpi_snapshot popolato (operational_kpis + compliance summary)
    assert isinstance(out.kpi_snapshot, dict)
    assert "operational_kpis" in out.kpi_snapshot


def test_generate_snapshot_returns_structured_dict(review, user):
    from apps.management_review.services import generate_snapshot
    snap = generate_snapshot(review, user)
    assert isinstance(snap, dict)
    # le sezioni principali del read-model esistono anche con plant "vuoto"
    for key in ("frameworks", "documenti", "rischi", "incidenti", "pdca", "bcp", "task"):
        assert key in snap, f"manca sezione {key}"


def test_approve_review_requires_snapshot(review, user):
    from apps.management_review.services import approve_review
    # senza snapshot_generated_at → ValidationError
    with pytest.raises(ValidationError):
        approve_review(review, user)


def test_approve_review_ok_then_idempotent(review, user):
    from apps.management_review.services import approve_review
    review.snapshot_generated_at = timezone.now()
    review.save(update_fields=["snapshot_generated_at"])
    out = approve_review(review, user, note="ok")
    out.refresh_from_db()
    assert out.approval_status == "approvato"
    assert out.approved_by == user
    # seconda approvazione → errore
    with pytest.raises(ValidationError):
        approve_review(out, user)

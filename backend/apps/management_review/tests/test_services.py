"""P2-1 — copertura management_review/services.py (complete, snapshot, approve)."""
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="mrs", email="mrs@x.it", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


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
    with pytest.raises(ValidationError):  # riunione non ancora chiusa
        approve_review(review, user, note="ok")
    review.status = "completato"
    review.save(update_fields=["status"])
    out = approve_review(review, user, note="ok")
    out.refresh_from_db()
    assert out.approval_status == "approvato"
    assert out.approved_by == user
    # seconda approvazione → errore
    with pytest.raises(ValidationError):
        approve_review(out, user)


# ── Dettagli executive nello snapshot ──────────────────────────────────────────

def test_snapshot_lists_documents_risks_incidents_details(review, plant, user):
    from datetime import timedelta
    from apps.documents.models import Document
    from apps.incidents.models import Incident
    from apps.risk.models import RiskAssessment, RiskMitigationPlan
    from apps.management_review.services import generate_snapshot

    today = timezone.localdate()
    Document.objects.create(
        plant=plant, title="Policy scaduta", category="policy", document_type="policy",
        status="approvato", review_due_date=today - timedelta(days=5), owner=user,
    )
    Document.objects.create(
        plant=plant, title="Procedura in scadenza", category="procedura", document_type="procedura",
        status="approvato", review_due_date=today + timedelta(days=30),
        approved_at=timezone.now(),
    )
    RiskAssessment.objects.create(
        plant=plant, name="Ransomware MES", assessment_type="OT", status="completato",
        probability=5, impact=4, inherent_probability=5, inherent_impact=5, owner=user,
    )
    covered = RiskAssessment.objects.create(
        plant=plant, name="Phishing", assessment_type="IT", status="completato",
        probability=4, impact=4,
    )
    RiskMitigationPlan.objects.create(assessment=covered, action="MFA", due_date=today)
    RiskAssessment.objects.create(
        plant=plant, name="Accettato", assessment_type="IT", status="completato",
        probability=2, impact=2, risk_accepted_formally=True, risk_accepted_by=user,
    )
    Incident.objects.create(
        plant=plant, title="Malware linea 3", description="x", detected_at=timezone.now(),
        severity="alta", status="aperto",
    )

    snap = generate_snapshot(review, user)

    docs = snap["documenti"]
    assert [d["title"] for d in docs["elenco_scaduti"]] == ["Policy scaduta"]
    assert docs["elenco_scaduti"][0]["owner"] == "mrs@x.it"
    assert [d["title"] for d in docs["elenco_in_scadenza"]] == ["Procedura in scadenza"]
    assert docs["approvati_periodo"] == 1

    rischi = snap["rischi"]
    assert rischi["rosso"] == 2
    assert rischi["senza_piano"] == 1
    top = rischi["top_critici"]
    assert top[0]["name"] == "Ransomware MES"  # score più alto prima
    assert top[0]["inherent_score"] == 25 and top[0]["score"] == 20
    assert top[0]["has_plan"] is False
    assert next(r for r in top if r["name"] == "Phishing")["has_plan"] is True
    assert [r["name"] for r in rischi["elenco_accettati"]] == ["Accettato"]

    assert [i["title"] for i in snap["incidenti"]["elenco_aperti"]] == ["Malware linea 3"]
    assert "risks_by_owner" not in snap


def test_suggest_chair_prefers_plant_ciso_then_org(plant, user):
    from apps.governance.models import RoleAssignment
    from apps.management_review.services import suggest_chair

    assert suggest_chair(plant.id) is None
    org_ciso = User.objects.create_user(username="orgciso", email="o@x.it", password="x")
    RoleAssignment.objects.create(
        user=org_ciso, role="ciso", scope_type="org", valid_from=timezone.localdate(),
    )
    assert suggest_chair(plant.id) == org_ciso
    RoleAssignment.objects.create(
        user=user, role="ciso", scope_type="plant", scope_id=plant.id,
        valid_from=timezone.localdate(),
    )
    assert suggest_chair(plant.id) == user
    assert suggest_chair(None) == org_ciso

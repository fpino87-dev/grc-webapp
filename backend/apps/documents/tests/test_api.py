"""Test API documenti."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_DOCS = "/api/v1/documents/documents/"
URL_EVIDENCES = "/api/v1/documents/evidences/"


@pytest.fixture
def user(db):
    """Utente con scope org (vede tutti i documenti)."""
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="doc_user", email="doc@test.com", password="test")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="DOC-P", name="Plant DOC", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def document(db, plant, user):
    from apps.documents.models import Document
    return Document.objects.create(
        title="Policy Sicurezza",
        category="policy",
        document_type="policy",
        status="bozza",
        plant=plant,
        created_by=user,
    )


# ── Documents ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_documents_authenticated(client):
    resp = client.get(URL_DOCS)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_list_documents_unauthenticated():
    resp = APIClient().get(URL_DOCS)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_create_document(client, plant):
    payload = {
        "title": "Procedura Backup",
        "category": "procedura",
        "document_type": "procedura",
        "status": "bozza",
        "plant": str(plant.id),
    }
    resp = client.post(URL_DOCS, payload, format="json")
    assert resp.status_code == 201
    assert resp.data["title"] == "Procedura Backup"


@pytest.mark.django_db
def test_retrieve_document(client, document):
    resp = client.get(f"{URL_DOCS}{document.id}/")
    assert resp.status_code == 200
    assert resp.data["title"] == "Policy Sicurezza"


@pytest.mark.django_db
def test_patch_cannot_change_workflow_status(client, document):
    """Lo stato del workflow non è scrivibile via PATCH: si cambia solo con le
    azioni submit/approve/reject/archive, che verificano policy e tracciano."""
    resp = client.patch(f"{URL_DOCS}{document.id}/", {"status": "revisione"}, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "bozza"
    document.refresh_from_db()
    assert document.status == "bozza"


@pytest.mark.django_db
def test_patch_cannot_self_approve(client, document, user):
    """Il bypass più grave: PATCH che porta ad approvato senza approvazione
    tracciata (né DocumentApproval né audit)."""
    from apps.documents.models import DocumentApproval

    resp = client.patch(
        f"{URL_DOCS}{document.id}/",
        {"status": "approvato", "approver": user.id, "approved_at": "2026-01-01T00:00:00Z"},
        format="json",
    )
    assert resp.status_code == 200
    document.refresh_from_db()
    assert document.status == "bozza"
    assert document.approver is None
    assert document.approved_at is None
    assert not DocumentApproval.objects.filter(document=document).exists()


@pytest.mark.django_db
def test_approve_rejected_from_bozza(client, document):
    """Salto di stato bozza → approvato: rifiutato dalla macchina a stati."""
    resp = client.post(f"{URL_DOCS}{document.id}/approve/", {}, format="json")
    assert resp.status_code == 400
    document.refresh_from_db()
    assert document.status == "bozza"


@pytest.mark.django_db
def test_submit_then_approve_flow(client, document):
    resp = client.post(f"{URL_DOCS}{document.id}/submit/", {}, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "revisione"

    resp = client.post(f"{URL_DOCS}{document.id}/approve/", {"notes": "ok"}, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "approvato"

    # archiviazione: consentita solo da approvato
    resp = client.post(f"{URL_DOCS}{document.id}/archive/", {}, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "archiviato"


@pytest.mark.django_db
def test_mandatory_document_without_policy_cannot_be_approved(client, document):
    """Deny by default: un documento obbligatorio non va in vigore se la
    governance non ha dichiarato chi approva quel tipo di documento."""
    document.is_mandatory = True
    document.status = "revisione"
    document.save(update_fields=["is_mandatory", "status"])

    resp = client.post(f"{URL_DOCS}{document.id}/approve/", {}, format="json")
    assert resp.status_code == 403
    document.refresh_from_db()
    assert document.status == "revisione"


@pytest.mark.django_db
def test_reject_requires_review_permission(client, document, plant):
    """Il rifiuto ora richiede il permesso di revisione da policy."""
    from apps.governance.models import DocumentWorkflowPolicy, NormativeRole

    DocumentWorkflowPolicy.objects.create(
        document_type="policy", scope_type="org",
        submit_roles=[NormativeRole.COMPLIANCE_OFFICER],
        review_roles=[NormativeRole.CISO],
        approve_roles=[NormativeRole.CISO],
    )
    document.status = "revisione"
    document.save(update_fields=["status"])

    resp = client.post(f"{URL_DOCS}{document.id}/reject/", {"notes": "no"}, format="json")
    assert resp.status_code == 403
    document.refresh_from_db()
    assert document.status == "revisione"


@pytest.mark.django_db
def test_delete_document(client, document):
    resp = client.delete(f"{URL_DOCS}{document.id}/")
    assert resp.status_code == 204


@pytest.mark.django_db
def test_filter_documents_by_plant(client, plant, document):
    resp = client.get(f"{URL_DOCS}?plant={plant.id}")
    assert resp.status_code == 200
    ids = [d["id"] for d in resp.data["results"]] if "results" in resp.data else [d["id"] for d in resp.data]
    assert str(document.id) in ids


@pytest.mark.django_db
def test_filter_documents_by_status(client, document):
    resp = client.get(f"{URL_DOCS}?status=bozza")
    assert resp.status_code == 200


# ── Evidences ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_evidences(client):
    resp = client.get(URL_EVIDENCES)
    assert resp.status_code == 200


# ── RBAC plant scoping (S1) ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_pm_does_not_see_documents_of_other_plant(db):
    """PM A vede documenti di Plant A + condivisi con A + org-wide; non vede solo Plant B."""
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    from apps.documents.models import Document
    from apps.plants.models import Plant

    plant_a = Plant.objects.create(
        code="DOC-A", name="A", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )
    plant_b = Plant.objects.create(
        code="DOC-B", name="B", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )
    Document.objects.create(plant=plant_a, title="Doc A", category="policy", status="bozza")
    Document.objects.create(plant=plant_b, title="Doc B", category="policy", status="bozza")
    Document.objects.create(plant=None, title="Doc Global", category="policy", status="bozza")
    shared = Document.objects.create(plant=plant_b, title="Doc Shared", category="policy", status="bozza")
    shared.shared_plants.add(plant_a)

    pm = User.objects.create_user(username="pm_doc", email="pmdoc@test", password="x")
    access = UserPlantAccess.objects.create(
        user=pm, role=GrcRole.PLANT_MANAGER, scope_type="single_plant",
    )
    access.scope_plants.set([plant_a])

    c = APIClient()
    c.force_authenticate(user=pm)
    resp = c.get(URL_DOCS)
    assert resp.status_code == 200
    titles = {item["title"] for item in resp.data["results"]}
    assert "Doc A" in titles
    assert "Doc Global" in titles
    assert "Doc Shared" in titles
    assert "Doc B" not in titles

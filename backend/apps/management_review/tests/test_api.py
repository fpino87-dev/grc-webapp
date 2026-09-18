"""Test API revisione direzione."""
import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_REVIEWS = "/api/v1/management-review/reviews/"
URL_ACTIONS = "/api/v1/management-review/review-actions/"


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="mr_user", email="mr@test.com", password="test")
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
        code="MR-P", name="Plant MR", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def review(db, plant, user):
    from apps.management_review.models import ManagementReview
    return ManagementReview.objects.create(
        plant=plant,
        title="Revisione Q1 2026",
        review_date=timezone.localdate(),
        status="pianificato",
        created_by=user,
    )


@pytest.fixture
def action(db, review, user):
    from apps.management_review.models import ReviewAction
    return ReviewAction.objects.create(
        review=review,
        description="Implementare controllo accessi",
        owner=user,
        due_date=timezone.localdate(),
        status="aperto",
        created_by=user,
    )


# ── Reviews ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_reviews_authenticated(client):
    resp = client.get(URL_REVIEWS)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_list_reviews_unauthenticated():
    resp = APIClient().get(URL_REVIEWS)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_create_review(client, plant):
    payload = {
        "plant": str(plant.id),
        "title": "Revisione Annuale 2026",
        "review_date": str(timezone.localdate()),
        "status": "pianificato",
    }
    resp = client.post(URL_REVIEWS, payload, format="json")
    assert resp.status_code == 201
    assert resp.data["title"] == "Revisione Annuale 2026"
    codes = [i["code"] for i in resp.data["agenda_items"]]
    assert codes == ["azioni_precedenti", "contesto", "parti_interessate", "prestazioni",
                     "feedback_parti", "rischi", "miglioramento"]


@pytest.mark.django_db
def test_retrieve_review(client, review):
    resp = client.get(f"{URL_REVIEWS}{review.id}/")
    assert resp.status_code == 200
    assert resp.data["title"] == "Revisione Q1 2026"


@pytest.mark.django_db
def test_update_review(client, review):
    resp = client.patch(f"{URL_REVIEWS}{review.id}/", {"title": "Nuovo titolo", "status": "completato"}, format="json")
    assert resp.status_code == 200
    assert resp.data["title"] == "Nuovo titolo"
    # lo stato passa solo dalle azioni start/complete (la chiusura verifica l'OdG)
    assert resp.data["status"] == "pianificato"


@pytest.mark.django_db
def test_cannot_self_approve_via_patch(client, review):
    """L'approvazione formale (ISO 9.3) non è impostabile con una PATCH diretta:
    né lo stato di approvazione né uno snapshot fittizio per sbloccarla."""
    resp = client.patch(
        f"{URL_REVIEWS}{review.id}/",
        {
            "approval_status": "approvato",
            "snapshot_generated_at": timezone.now().isoformat(),
        },
        format="json",
    )
    assert resp.status_code == 200
    review.refresh_from_db()
    assert review.approval_status == "bozza"
    assert review.approved_by is None
    assert review.snapshot_generated_at is None


@pytest.mark.django_db
def test_approve_requires_snapshot(client, review):
    """L'azione approve è bloccata finché non si genera lo snapshot dati."""
    resp = client.post(f"{URL_REVIEWS}{review.id}/approve/", {"note": "ok"}, format="json")
    assert resp.status_code == 400
    review.refresh_from_db()
    assert review.approval_status == "bozza"


@pytest.mark.django_db
def test_delete_review(client, review):
    resp = client.delete(f"{URL_REVIEWS}{review.id}/")
    assert resp.status_code == 204


@pytest.mark.django_db
def test_filter_reviews_by_plant(client, plant, review):
    resp = client.get(f"{URL_REVIEWS}?plant={plant.id}")
    assert resp.status_code == 200


# ── Review actions ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_review_actions(client):
    resp = client.get(URL_ACTIONS)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_create_review_action(client, review, user):
    payload = {
        "review": str(review.id),
        "description": "Aggiornare documentazione sicurezza",
        "owner": str(user.id),
        "due_date": str(timezone.localdate()),
        "status": "aperto",
    }
    resp = client.post(URL_ACTIONS, payload, format="json")
    assert resp.status_code == 201


@pytest.mark.django_db
def test_retrieve_review_action(client, action):
    resp = client.get(f"{URL_ACTIONS}{action.id}/")
    assert resp.status_code == 200
    assert resp.data["description"] == "Implementare controllo accessi"


@pytest.mark.django_db
def test_update_review_action(client, action):
    resp = client.patch(f"{URL_ACTIONS}{action.id}/", {"status": "chiuso"}, format="json")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_delete_review_action_soft(client, action):
    resp = client.delete(f"{URL_ACTIONS}{action.id}/")
    assert resp.status_code == 204
    from apps.management_review.models import ReviewAction
    action.refresh_from_db()
    assert action.deleted_at is not None
    assert ReviewAction.objects.filter(pk=action.pk).count() == 0
    assert ReviewAction.objects.all_with_deleted().filter(pk=action.pk).count() == 1


@pytest.mark.django_db
def test_set_participants_with_guest(client, review, user):
    other = User.objects.create_user(username="att", email="att@test.com", password="x",
                                     first_name="Anna", last_name="Rossi")
    resp = client.put(f"{URL_REVIEWS}{review.id}/participants/", {"participants": [
        {"user": user.id, "is_chair": True, "body_role": "presidente"},
        {"user": other.id, "attendance": "assente"},
        {"full_name": "Mario Bianchi", "position": "Consulente esterno"},
    ]}, format="json")
    assert resp.status_code == 200, resp.data
    assert resp.data["chair_name"] == "mr@test.com"
    rows = {p["full_name"]: p for p in resp.data["participants"]}
    assert rows["Anna Rossi"]["attendance"] == "assente"
    assert rows["Mario Bianchi"]["body_role"] == "ospite" and not rows["Mario Bianchi"]["has_account"]


@pytest.mark.django_db
def test_participants_not_editable_after_approval(client, review, user):
    review.approval_status = "approvato"
    review.save(update_fields=["approval_status"])
    resp = client.put(f"{URL_REVIEWS}{review.id}/participants/",
                      {"participants": [{"user": user.id, "is_chair": True}]}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_suggested_chair_endpoint(client, plant):
    resp = client.get(f"{URL_REVIEWS}suggested-chair/", {"plant": str(plant.id)})
    assert resp.status_code == 200
    assert resp.data == {"id": None, "name": None}
    assert client.get(f"{URL_REVIEWS}suggested-chair/", {"plant": "nope"}).status_code == 400


@pytest.mark.django_db
def test_report_escapes_user_content(client, review):
    review.title = "<script>alert(1)</script>"
    review.snapshot_data = {"generated_at": timezone.now().isoformat(), "documenti": {
        "elenco_scaduti": [{"title": "<img src=x onerror=alert(1)>", "owner": None, "review_due_date": "2026-01-01"}],
    }}
    review.snapshot_generated_at = timezone.now()
    review.save()
    resp = client.get(f"{URL_REVIEWS}{review.id}/report/")
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "<script>alert(1)" not in body and "<img src=x" not in body
    assert "&lt;img src=x" in body


@pytest.mark.django_db
def test_snapshot_not_regenerated_after_approval(client, review):
    review.approval_status = "approvato"
    review.snapshot_data = {"generated_at": "2026-01-01T00:00:00"}
    review.save(update_fields=["approval_status", "snapshot_data"])
    resp = client.post(f"{URL_REVIEWS}{review.id}/generate-snapshot/")
    assert resp.status_code == 400
    review.refresh_from_db()
    assert review.snapshot_data == {"generated_at": "2026-01-01T00:00:00"}

"""Test API revisione direzione."""
import pytest
from datetime import date
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_REVIEWS = "/api/v1/management-review/reviews/"
URL_ACTIONS = "/api/v1/management-review/review-actions/"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="mr_user", email="mr@test.com", password="test")


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
        review_date=date.today(),
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
        due_date=date.today(),
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
        "review_date": str(date.today()),
        "status": "pianificato",
    }
    resp = client.post(URL_REVIEWS, payload, format="json")
    assert resp.status_code == 201
    assert resp.data["title"] == "Revisione Annuale 2026"


@pytest.mark.django_db
def test_retrieve_review(client, review):
    resp = client.get(f"{URL_REVIEWS}{review.id}/")
    assert resp.status_code == 200
    assert resp.data["title"] == "Revisione Q1 2026"


@pytest.mark.django_db
def test_update_review(client, review):
    resp = client.patch(f"{URL_REVIEWS}{review.id}/", {"status": "completato"}, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "completato"


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
        "due_date": str(date.today()),
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
def test_delete_review_action(client, action):
    resp = client.delete(f"{URL_ACTIONS}{action.id}/")
    assert resp.status_code == 204

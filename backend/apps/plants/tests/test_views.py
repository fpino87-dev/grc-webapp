"""P2-1 — copertura views.py del modulo plants (M01).

Copre: PlantViewSet.update (blocco cambio codice, warning incidenti aperti),
destroy (blocco dipendenze, force superuser), upload_logo / logo (open-redirect
guard), PlantFrameworkViewSet (toggle_active, generazione/soft-delete
ControlInstance).
"""
import base64
import datetime

import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient

from apps.plants.models import PlantFramework

User = get_user_model()

# 1x1 PNG valido — riconosciuto come image/png da libmagic (MIME check upload).
_PNG_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNk"
    "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


@pytest.fixture
def framework_iso(db):
    from apps.controls.models import Framework

    return Framework.objects.create(
        code="ISO27001", name="ISO 27001:2022", version="2022",
        published_at=datetime.date(2022, 10, 25),
    )


@pytest.fixture
def control_iso(framework_iso):
    from apps.controls.models import Control

    return Control.objects.create(
        framework=framework_iso, external_id="A.5.1",
        translations={"it": {"title": "Policy"}},
    )


@pytest.fixture
def superclient(db):
    su = User.objects.create_superuser(
        username="root", email="root@test.com", password="test-pw-123456",
    )
    client = APIClient()
    client.force_authenticate(user=su)
    return client


# ── PlantViewSet.update ─────────────────────────────────────────────────────


@pytest.mark.django_db
def test_update_blocks_code_change_with_control_instances(api_client, plant_nis2, control_iso):
    from apps.controls.models import ControlInstance

    ControlInstance.objects.create(
        plant=plant_nis2, control=control_iso, status="non_valutato",
    )
    url = reverse("plant-detail", args=[plant_nis2.id])
    resp = api_client.patch(url, {"code": "CHANGED"})
    assert resp.status_code == 400
    assert "error" in resp.data
    plant_nis2.refresh_from_db()
    assert plant_nis2.code == "NIS2-TEST"  # invariato


@pytest.mark.django_db
def test_update_same_code_is_allowed(api_client, plant_nis2, control_iso):
    from apps.controls.models import ControlInstance

    ControlInstance.objects.create(
        plant=plant_nis2, control=control_iso, status="non_valutato",
    )
    url = reverse("plant-detail", args=[plant_nis2.id])
    resp = api_client.patch(url, {"code": "NIS2-TEST", "name": "Rinominato"})
    assert resp.status_code == 200
    plant_nis2.refresh_from_db()
    assert plant_nis2.name == "Rinominato"


@pytest.mark.django_db
def test_update_warns_on_open_incidents(api_client, plant_nis2):
    from apps.incidents.models import Incident
    from django.utils import timezone

    Incident.objects.create(
        plant=plant_nis2, title="Down", description="x",
        detected_at=timezone.now(), severity="alta", status="aperto",
    )
    url = reverse("plant-detail", args=[plant_nis2.id])
    resp = api_client.patch(url, {"name": "Nuovo nome"})
    assert resp.status_code == 200
    assert "_warning" in resp.data


# ── PlantViewSet.destroy ────────────────────────────────────────────────────


@pytest.mark.django_db
def test_destroy_blocked_by_dependency_returns_400(api_client, plant_nis2):
    from apps.assets.models import Asset

    Asset.objects.create(plant=plant_nis2, name="Srv", asset_type="IT", criticality=2)
    url = reverse("plant-detail", args=[plant_nis2.id])
    resp = api_client.delete(url)
    assert resp.status_code == 400
    assert resp.data["blocking"]["assets"] == 1
    plant_nis2.refresh_from_db()
    assert plant_nis2.deleted_at is None


@pytest.mark.django_db
def test_destroy_force_requires_superuser(api_client, plant_nis2):
    from apps.assets.models import Asset

    Asset.objects.create(plant=plant_nis2, name="Srv", asset_type="IT", criticality=2)
    url = reverse("plant-detail", args=[plant_nis2.id]) + "?force=true"
    resp = api_client.delete(url)
    # co_user non e' superuser -> ValidationError -> 400
    assert resp.status_code == 400
    plant_nis2.refresh_from_db()
    assert plant_nis2.deleted_at is None


@pytest.mark.django_db
def test_destroy_force_superuser_cascades(superclient, plant_nis2):
    from apps.assets.models import Asset

    asset = Asset.objects.create(plant=plant_nis2, name="Srv", asset_type="IT", criticality=2)
    url = reverse("plant-detail", args=[plant_nis2.id]) + "?force=true"
    resp = superclient.delete(url)
    assert resp.status_code == 204
    plant_nis2.refresh_from_db()
    asset.refresh_from_db()
    assert plant_nis2.deleted_at is not None
    assert asset.deleted_at is not None


# ── upload_logo / logo ──────────────────────────────────────────────────────


@pytest.mark.django_db
def test_upload_logo_no_file_returns_400(api_client, plant_nis2):
    url = reverse("plant-upload-logo", args=[plant_nis2.id])
    resp = api_client.post(url, {}, format="multipart")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_upload_logo_success_sets_logo_url(api_client, plant_nis2):
    url = reverse("plant-upload-logo", args=[plant_nis2.id])
    upload = SimpleUploadedFile("logo.png", _PNG_1x1, content_type="image/png")
    resp = api_client.post(url, {"file": upload}, format="multipart")
    assert resp.status_code == 200, resp.data
    plant_nis2.refresh_from_db()
    assert plant_nis2.logo_url
    assert f"plant-logos/{plant_nis2.id}/" in plant_nis2.logo_url


@pytest.mark.django_db
def test_upload_logo_rejects_non_image(api_client, plant_nis2):

    url = reverse("plant-upload-logo", args=[plant_nis2.id])
    upload = SimpleUploadedFile("evil.png", b"#!/bin/sh\necho hi", content_type="image/png")
    # validate_uploaded_file solleva su MIME reale non immagine
    with pytest.raises(Exception):
        api_client.post(url, {"file": upload}, format="multipart")


@pytest.mark.django_db
def test_logo_no_logo_configured_returns_404(api_client, plant_nis2):
    url = reverse("plant-logo", args=[plant_nis2.id])
    resp = api_client.get(url)
    assert resp.status_code == 404


@pytest.mark.django_db
def test_logo_external_url_rejected(api_client, plant_nis2):
    """Open-redirect / SSRF guard: logo_url esterno -> 404, mai redirect."""
    plant_nis2.logo_url = "https://evil.example.com/logo.png"
    plant_nis2.save(update_fields=["logo_url"])
    url = reverse("plant-logo", args=[plant_nis2.id])
    resp = api_client.get(url)
    assert resp.status_code == 404


@pytest.mark.django_db
def test_logo_upload_then_serve(api_client, plant_nis2):
    upload = SimpleUploadedFile("logo.png", _PNG_1x1, content_type="image/png")
    up_url = reverse("plant-upload-logo", args=[plant_nis2.id])
    assert api_client.post(up_url, {"file": upload}, format="multipart").status_code == 200

    serve_url = reverse("plant-logo", args=[plant_nis2.id])
    resp = api_client.get(serve_url)
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("image/")


# ── PlantFrameworkViewSet ───────────────────────────────────────────────────


@pytest.mark.django_db
def test_plant_framework_create_generates_control_instances(api_client, plant_nis2, framework_iso, control_iso):
    from apps.controls.models import ControlInstance

    url = reverse("plant-framework-list")
    resp = api_client.post(url, {
        "plant": str(plant_nis2.id),
        "framework": str(framework_iso.id),
    })
    assert resp.status_code == 201, resp.data
    assert ControlInstance.objects.filter(plant=plant_nis2, control=control_iso).exists()


@pytest.mark.django_db
def test_plant_framework_destroy_soft_deletes_control_instances(api_client, plant_nis2, framework_iso, control_iso):
    from apps.controls.models import ControlInstance

    pf = PlantFramework.objects.create(
        plant=plant_nis2, framework=framework_iso, active_from=timezone.localdate(),
    )
    ci = ControlInstance.objects.create(
        plant=plant_nis2, control=control_iso, status="non_valutato",
    )
    url = reverse("plant-framework-detail", args=[pf.id])
    resp = api_client.delete(url)
    assert resp.status_code == 204
    ci.refresh_from_db()
    assert ci.deleted_at is not None


@pytest.mark.django_db
def test_plant_framework_toggle_active(api_client, plant_nis2, framework_iso):
    pf = PlantFramework.objects.create(
        plant=plant_nis2, framework=framework_iso,
        active_from=timezone.localdate(), active=True,
    )
    url = reverse("plant-framework-toggle-active", args=[pf.id])
    resp = api_client.post(url)
    assert resp.status_code == 200
    pf.refresh_from_db()
    assert pf.active is False


@pytest.mark.django_db
def test_plant_framework_list_filtered_by_plant(api_client, plant_nis2, plant_tisax, framework_iso):
    PlantFramework.objects.create(
        plant=plant_nis2, framework=framework_iso, active_from=timezone.localdate(),
    )
    url = reverse("plant-framework-list") + f"?plant={plant_nis2.id}"
    resp = api_client.get(url)
    assert resp.status_code == 200
    rows = resp.data.get("results", resp.data)
    assert rows  # almeno un risultato
    assert all(str(r["plant"]) == str(plant_nis2.id) for r in rows)

"""Logo del verbale: scelto tra i loghi dei siti già caricati, accessibili
all'utente; incorporato in HTML e PDF."""
import base64
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework.test import APIClient

User = get_user_model()

URL = "/api/v1/management-review/reviews/"

# PNG 1x1 valido (Pillow/ReportLab lo leggono)
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNk"
    "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _plant(code, logo=True, ext="png"):
    from apps.plants.models import Plant
    p = Plant.objects.create(code=code, name=f"Sito {code}", country="IT",
                             nis2_scope="non_soggetto", status="attivo")
    if logo:
        path = default_storage.save(f"plant-logos/{p.id}/logo.{ext}", ContentFile(PNG))
        p.logo_url = f"/media/{path}"
        p.save(update_fields=["logo_url"])
    return p


def _client(role="compliance_officer", scope="org", plants=()):
    from apps.auth_grc.models import UserPlantAccess
    u = User.objects.create_user(username=f"rl_{role}_{scope}", email=f"{role}{scope}@rl.test", password="x")
    acc = UserPlantAccess.objects.create(user=u, role=role, scope_type=scope)
    for p in plants:
        acc.scope_plants.add(p)
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.mark.django_db
def test_plant_logo_helper_rules():
    from apps.plants.services import plant_logo, plant_logo_data_uri
    p = _plant("RL-1", ext="jpeg")
    data, mime = plant_logo(p)
    assert data == PNG and mime == "image/jpeg"  # MIME dall'estensione, non sempre png
    assert plant_logo_data_uri(p).startswith("data:image/jpeg;base64,")

    other = _plant("RL-2")
    p.logo_url = other.logo_url  # file di un altro sito: fuori cartella
    assert plant_logo(p) is None
    p.logo_url = f"/media/plant-logos/{p.id}/../../secret.png"
    assert plant_logo(p) is None
    p.logo_url = "https://evil.example/logo.png"
    assert plant_logo(p) is None
    assert plant_logo(_plant("RL-3", logo=False)) is None


@pytest.mark.django_db
def test_create_proposes_site_logo():
    p = _plant("RL-4")
    resp = _client().post(URL, {"title": "R", "review_date": "2026-03-01", "plant": str(p.id)}, format="json")
    assert resp.status_code == 201, resp.data
    assert resp.data["report_logo_plant"] == p.id


@pytest.mark.django_db
def test_choose_logo_checks_access_and_logo():
    from apps.management_review.models import ManagementReview
    mine, other, bare = _plant("RL-5"), _plant("RL-6"), _plant("RL-7", logo=False)
    review = ManagementReview.objects.create(title="R", review_date=date(2026, 3, 1), plant=mine)
    client = _client(scope="single_plant", plants=[mine, bare])

    assert client.post(f"{URL}{review.id}/report-logo/", {"plant": str(other.id)}, format="json").status_code == 400
    assert client.post(f"{URL}{review.id}/report-logo/", {"plant": str(bare.id)}, format="json").status_code == 400
    resp = client.post(f"{URL}{review.id}/report-logo/", {"plant": str(mine.id)}, format="json")
    assert resp.status_code == 200 and resp.data["report_logo_plant_code"] == "RL-5"
    resp = client.post(f"{URL}{review.id}/report-logo/", {"plant": None}, format="json")
    assert resp.status_code == 200 and resp.data["report_logo_plant"] is None


@pytest.mark.django_db
def test_logo_changeable_after_approval_and_rendered():
    from apps.management_review.models import ManagementReview
    from apps.management_review.report import render_pdf
    from apps.management_review.report.html import render_html
    p = _plant("RL-8")
    review = ManagementReview.objects.create(
        title="R", review_date=date(2026, 3, 1), status="completato", approval_status="approvato",
        snapshot_generated_at=timezone.now(), snapshot_data={"generated_at": timezone.now().isoformat()},
    )
    resp = _client().post(f"{URL}{review.id}/report-logo/", {"plant": str(p.id)}, format="json")
    assert resp.status_code == 200  # presentazione, non contenuto del verbale

    review.refresh_from_db()
    assert "data:image/png;base64," in render_html(review)
    from apps.management_review.report.builder import build_report
    from apps.management_review.report.pdf import _logo_flowable
    logo = build_report(review)["logo"]
    img = _logo_flowable(logo)
    assert img is not None and img.drawHeight <= 16 * 2.8346 + 0.01  # entro 16 mm
    with_logo = render_pdf(review)
    review.report_logo_plant = None
    review.save(update_fields=["report_logo_plant"])
    without = render_pdf(review)
    assert with_logo.startswith(b"%PDF") and len(with_logo) > len(without)
    # un file illeggibile non blocca il verbale
    assert _logo_flowable({"data": b"not an image", "mime": "image/png"}) is None


@pytest.mark.django_db
def test_body_member_cannot_change_logo():
    from apps.governance.models import CommitteeMember, SecurityCommittee
    from apps.management_review.models import ManagementReview
    p = _plant("RL-9")
    director = User.objects.create_user(username="rl_dir", email="d@rl.test", password="x")
    body = SecurityCommittee.objects.create(name="CdA", committee_type="cda")
    CommitteeMember.objects.create(committee=body, full_name="D", user=director, valid_from=date(2025, 1, 1))
    review = ManagementReview.objects.create(title="R", review_date=date(2026, 3, 1), governing_body=body)
    c = APIClient()
    c.force_authenticate(user=director)
    assert c.post(f"{URL}{review.id}/report-logo/", {"plant": str(p.id)}, format="json").status_code == 403

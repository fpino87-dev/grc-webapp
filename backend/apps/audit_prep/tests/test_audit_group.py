"""Audit multi-sito (es. TISAX AL2 su 2 stabilimenti): un AuditPrep per sito
legati da un AuditGroup con dati e rapporto condivisi, finding comuni."""
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

User = get_user_model()

URL_GROUPS = "/api/v1/audit-prep/audit-groups/"
URL_PREPS = "/api/v1/audit-prep/audit-preps/"
URL_FINDINGS = "/api/v1/audit-prep/findings/"


@pytest.fixture(autouse=True)
def _media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)


def _plant(code):
    from apps.plants.models import Plant
    return Plant.objects.create(code=code, name=f"Plant {code}", country="IT", nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def plants(db):
    return _plant("TA"), _plant("TB"), _plant("TC")


@pytest.fixture
def tisax(db, plants):
    from apps.controls.models import Framework
    from apps.plants.models import PlantFramework
    fw = Framework.objects.create(code="TISAX_L2", name="TISAX AL2", version="6.0", published_at=timezone.localdate())
    for p in plants[:2]:
        PlantFramework.objects.create(plant=p, framework=fw, active_from=timezone.localdate())
    return fw


def _user(name, role, plants=None):
    from apps.auth_grc.models import UserPlantAccess
    u = User.objects.create_user(username=name, email=f"{name}@test.com", password="x")
    if plants is None:
        UserPlantAccess.objects.create(user=u, role=role, scope_type="org")
    else:
        acc = UserPlantAccess.objects.create(user=u, role=role, scope_type="single_plant")
        acc.scope_plants.set(plants)
    return u


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def co(db):
    from apps.auth_grc.models import GrcRole
    return _user("grp_co", GrcRole.COMPLIANCE_OFFICER)


@pytest.fixture
def group(co, plants, tisax):
    resp = _client(co).post(URL_GROUPS, {
        "title": "TISAX AL2 2026", "plants": [str(plants[0].id), str(plants[1].id)],
        "framework": str(tisax.id), "audit_type": "terza_parte", "auditor_name": "Ente Gamma",
        "audit_date": "2026-10-05", "scope_id": "S12345",
    }, format="json")
    assert resp.status_code == 201, resp.data
    return resp.data


def _pdf():
    return SimpleUploadedFile("rapporto.pdf", b"%PDF-1.4 rapporto TISAX", content_type="application/pdf")


# ── Creazione ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_group_makes_one_prep_per_site(group, plants):
    from apps.audit_prep.models import AuditPrep
    assert [p["plant_code"] for p in group["preps"]] == ["TA", "TB"]
    preps = AuditPrep.objects.filter(group_id=group["id"]).order_by("plant__code")
    assert [p.title for p in preps] == ["TISAX AL2 2026 — TA", "TISAX AL2 2026 — TB"]
    for p in preps:
        assert (p.audit_type, p.auditor_name, str(p.audit_date)) == ("terza_parte", "Ente Gamma", "2026-10-05")
        assert p.framework.code == "TISAX_L2"


@pytest.mark.django_db
def test_group_needs_two_sites_and_framework_on_each(co, plants, tisax):
    c = _client(co)
    assert c.post(URL_GROUPS, {"title": "x", "plants": [str(plants[0].id)]}, format="json").status_code == 400
    resp = c.post(URL_GROUPS, {"title": "x", "plants": [str(plants[0].id), str(plants[2].id)],
                               "framework": str(tisax.id)}, format="json")
    assert resp.status_code == 400
    assert "TC" in str(resp.data)


@pytest.mark.django_db
def test_site_user_cannot_create_group_including_other_site(plants):
    from apps.auth_grc.models import GrcRole
    u = _user("grp_ia", GrcRole.INTERNAL_AUDITOR, plants=[plants[0]])
    resp = _client(u).post(URL_GROUPS, {"title": "x", "plants": [str(plants[0].id), str(plants[1].id)]},
                           format="json")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_prep_exposes_group_sites(co, group):
    prep_id = group["preps"][0]["id"]
    data = _client(co).get(f"{URL_PREPS}{prep_id}/").data
    assert str(data["group"]) == group["id"]
    assert data["group_title"] == "TISAX AL2 2026"
    assert data["group_scope_id"] == "S12345"
    assert [s["plant_code"] for s in data["group_sites"]] == ["TA", "TB"]


# ── Dati comuni ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_group_update_propagates_to_sites(co, group):
    from apps.audit_prep.models import AuditPrep
    resp = _client(co).patch(f"{URL_GROUPS}{group['id']}/", {
        "audit_type": "seconda_parte", "requesting_party": "OEM Alfa", "audit_date": "2026-10-12",
    }, format="json")
    assert resp.status_code == 200, resp.data
    for p in AuditPrep.objects.filter(group_id=group["id"]):
        assert (p.audit_type, p.requesting_party, str(p.audit_date)) == ("seconda_parte", "OEM Alfa", "2026-10-12")


@pytest.mark.django_db
def test_shared_fields_not_editable_from_single_site(co, group):
    c = _client(co)
    prep_id = group["preps"][0]["id"]
    assert c.patch(f"{URL_PREPS}{prep_id}/", {"auditor_name": "Altro"}, format="json").status_code == 400
    # i campi del singolo sito restano modificabili
    assert c.patch(f"{URL_PREPS}{prep_id}/", {"title": "Solo questo sito"}, format="json").status_code == 200


@pytest.mark.django_db
def test_site_user_sees_group_but_cannot_change_it(group, plants):
    from apps.auth_grc.models import GrcRole
    u = _user("grp_ia2", GrcRole.INTERNAL_AUDITOR, plants=[plants[0]])
    c = _client(u)
    assert [g["id"] for g in c.get(URL_GROUPS).data["results"]] == [group["id"]]
    assert c.patch(f"{URL_GROUPS}{group['id']}/", {"auditor_name": "x"}, format="json").status_code == 403
    prep_ta = group["preps"][0]["id"]
    assert c.post(f"{URL_PREPS}{prep_ta}/report-file/", {"file": _pdf()}, format="multipart").status_code == 403
    # vede solo il proprio sito tra gli audit
    assert [p["id"] for p in c.get(URL_PREPS).data["results"]] == [prep_ta]


# ── Rapporto comune ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_report_attached_once_for_all_sites_and_downloadable_from_each(co, group, plants):
    from apps.audit_prep.models import AuditPrep
    from apps.auth_grc.models import GrcRole
    from apps.documents.models import Evidence
    c = _client(co)
    prep_ta, prep_tb = (p["id"] for p in group["preps"])
    resp = c.post(f"{URL_PREPS}{prep_ta}/report-file/", {"file": _pdf()}, format="multipart")
    assert resp.status_code == 201, resp.data
    assert Evidence.objects.count() == 1
    ev = Evidence.objects.get()
    assert set(AuditPrep.objects.filter(group_id=group["id"]).values_list("report_evidence_id", flat=True)) == {ev.id}

    # un utente del solo sito TB scarica il rapporto dal proprio audit
    u = _user("grp_tb", GrcRole.INTERNAL_AUDITOR, plants=[plants[1]])
    resp = _client(u).get(f"{URL_PREPS}{prep_tb}/report-file/")
    assert resp.status_code == 200
    assert b"".join(resp.streaming_content).startswith(b"%PDF")

    assert c.delete(f"{URL_PREPS}{prep_tb}/report-file/").status_code == 204
    assert not AuditPrep.objects.filter(group_id=group["id"], report_evidence__isnull=False).exists()


@pytest.mark.django_db
def test_download_without_report_is_404(co, group):
    assert _client(co).get(f"{URL_PREPS}{group['preps'][0]['id']}/report-file/").status_code == 404


# ── Finding comuni ──────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_common_finding_opens_one_finding_and_pdca_per_site(co, group, plants):
    from apps.audit_prep.models import AuditFinding
    prep_ta = group["preps"][0]["id"]
    resp = _client(co).post(URL_FINDINGS, {
        "audit_prep": prep_ta, "finding_type": "minor_nc", "title": "Classificazione informazioni",
        "description": "Schema non applicato", "audit_date": "2026-10-05", "apply_to_group": True,
    }, format="json")
    assert resp.status_code == 201, resp.data
    assert str(resp.data["audit_prep"]) == prep_ta
    findings = list(AuditFinding.objects.filter(title="Classificazione informazioni").select_related(
        "audit_prep__plant", "pdca_cycle"))
    assert len(findings) == 2
    assert len({f.common_key for f in findings}) == 1 and findings[0].common_key
    assert {f.pdca_cycle.plant.code for f in findings} == {"TA", "TB"}
    assert {f.auditor_name for f in findings} == {"Ente Gamma"}


@pytest.mark.django_db
def test_site_finding_stays_on_its_site(co, group):
    from apps.audit_prep.models import AuditFinding
    resp = _client(co).post(URL_FINDINGS, {
        "audit_prep": group["preps"][1]["id"], "finding_type": "observation", "title": "Solo TB",
        "description": "d", "audit_date": "2026-10-05",
    }, format="json")
    assert resp.status_code == 201
    assert AuditFinding.objects.filter(title="Solo TB").count() == 1


# ── Riesame di direzione ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_org_review_counts_group_once_site_review_per_site(group, plants):
    from apps.management_review.services.snapshot import _audit_block
    today = timezone.localdate()
    since = timezone.now() - datetime.timedelta(days=365)
    org = _audit_block({}, today, since)
    assert org["audit_12m"] == 1
    row = org["elenco_audit"][0]
    assert row["title"] == "TISAX AL2 2026" and row["plant_code"] == "TA, TB"
    site = _audit_block({"plant_id": plants[0].id}, today, since)
    assert site["audit_12m"] == 1 and site["elenco_audit"][0]["title"] == "TISAX AL2 2026 — TA"

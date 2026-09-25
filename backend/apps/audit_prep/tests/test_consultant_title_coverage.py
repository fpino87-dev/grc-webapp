"""Audit interno affidato a un consulente esterno (gestito come la seconda
parte), titolo modificabile, copertura completa per l'audit singolo."""
import io
import zipfile

import pytest
from django.utils import timezone

from . import test_audit_group as grp
from . import test_external_audit as ext
from .test_external_audit import URL_PREPS, _pdf

user, client, plant, tisax_l3 = ext.user, ext.client, ext.plant, ext.tisax_l3
plants, tisax, co, group = grp.plants, grp.tisax, grp.co, grp.group


@pytest.fixture(autouse=True)
def _media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)


def _consultant_prep(client, plant, **extra):
    resp = client.post(URL_PREPS, {
        "plant": str(plant.id), "title": "Audit interno 2026", "audit_date": "2026-09-10",
        "audit_type": "interno", "external_consultant": True, "auditor_name": "Studio Rossi",
        **extra,
    }, format="json")
    assert resp.status_code == 201, resp.data
    return resp.data


# ── Consulente esterno ──────────────────────────────────────────────────────

@pytest.mark.django_db
def test_consultant_internal_audit_has_no_checklist(client, plant, tisax_l3):
    from apps.audit_prep.models import AuditPrep
    data = _consultant_prep(client, plant, framework=str(tisax_l3.id))
    prep = AuditPrep.objects.get(pk=data["id"])
    assert prep.uses_checklist is False
    assert prep.evidence_items.count() == 0
    url = f"{URL_PREPS}{prep.pk}/"
    resp = client.post(f"{url}auto-validate/")
    assert resp.status_code == 400 and "consulente" in resp.data["error"]
    assert client.get(f"{url}readiness/").data["readiness_score"] is None


@pytest.mark.django_db
def test_consultant_flag_only_for_internal(client, plant):
    resp = client.post(URL_PREPS, {
        "plant": str(plant.id), "title": "Terza", "audit_type": "terza_parte", "external_consultant": True,
    }, format="json")
    assert resp.status_code == 201 and resp.data["external_consultant"] is False
    data = _consultant_prep(client, plant)
    resp = client.patch(f"{URL_PREPS}{data['id']}/", {"audit_type": "terza_parte"}, format="json")
    assert resp.status_code == 200 and resp.data["external_consultant"] is False


@pytest.mark.django_db
def test_consultant_report_in_audit_package(client, plant):
    from django.core.files.storage import default_storage
    from apps.controls.views.audit_package import _add_external_audit_reports
    data = _consultant_prep(client, plant)
    client.post(f"{URL_PREPS}{data['id']}/report-file/", {"file": _pdf()}, format="multipart")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        _add_external_audit_reports(zf, "PKG", plant.id, default_storage)
    with zipfile.ZipFile(buf) as zf:
        index = zf.read("PKG/AUDIT_ESTERNI/RIEPILOGO.csv").decode("utf-8-sig")
        names = zf.namelist()
    assert "Studio Rossi" in index and "consulente esterno" in index
    assert any(n.endswith(".pdf") for n in names)


@pytest.mark.django_db
def test_group_consultant_flag_propagates(co, group):
    from apps.audit_prep.models import AuditPrep
    c = grp._client(co)
    resp = c.patch(f"{grp.URL_GROUPS}{group['id']}/", {"audit_type": "interno", "external_consultant": True},
                   format="json")
    assert resp.status_code == 200, resp.data
    preps = AuditPrep.objects.filter(group_id=group["id"])
    assert all(p.external_consultant and not p.uses_checklist for p in preps)


# ── Titolo ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_title_editable(client, plant):
    data = _consultant_prep(client, plant)
    resp = client.patch(f"{URL_PREPS}{data['id']}/", {"title": "Audit interno ISO 27001 — settembre"}, format="json")
    assert resp.status_code == 200 and resp.data["title"] == "Audit interno ISO 27001 — settembre"


@pytest.mark.django_db
def test_group_title_renames_site_audits(co, group):
    from apps.audit_prep.models import AuditPrep
    resp = grp._client(co).patch(f"{grp.URL_GROUPS}{group['id']}/", {"title": "TISAX AL2 rinnovo"}, format="json")
    assert resp.status_code == 200, resp.data
    titles = sorted(AuditPrep.objects.filter(group_id=group["id"]).values_list("title", flat=True))
    assert titles == ["TISAX AL2 rinnovo — TA", "TISAX AL2 rinnovo — TB"]


# ── Copertura ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_standalone_audit_is_full_coverage(client, plant):
    resp = client.post(URL_PREPS, {"plant": str(plant.id), "title": "Singolo", "coverage_type": "campione"},
                       format="json")
    assert resp.status_code == 201 and resp.data["coverage_type"] == "full"
    resp = client.patch(f"{URL_PREPS}{resp.data['id']}/", {"coverage_type": "campione"}, format="json")
    assert resp.data["coverage_type"] == "full"


@pytest.mark.django_db
def test_group_audits_are_full_coverage(group):
    from apps.audit_prep.models import AuditPrep
    assert set(AuditPrep.objects.filter(group_id=group["id"]).values_list("coverage_type", flat=True)) == {"full"}


@pytest.mark.django_db
def test_program_audit_keeps_its_coverage(user, plant):
    from apps.audit_prep.models import AuditPrep, AuditProgram
    program = AuditProgram.objects.create(plant=plant, year=2026, title="P", status="approvato", created_by=user)
    prep = AuditPrep.objects.create(plant=plant, title="Q1", audit_program=program, coverage_type="campione",
                                    audit_date=timezone.localdate(), created_by=user)
    assert prep.coverage_type == "campione"

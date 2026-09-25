"""Osservazioni e opportunità non perseguite: motivo obbligatorio, prova
facoltativa, PDCA collegato archiviato, rilievo comune su tutti i siti,
riapertura; le non conformità seguono il PDCA."""
import datetime

import pytest
from django.utils import timezone

from . import test_audit_group as grp
from . import test_external_audit as ext
from .test_external_audit import URL_FINDINGS, _pdf

user, client, plant, prep = ext.user, ext.client, ext.plant, ext.prep
plants, tisax, co, group = grp.plants, grp.tisax, grp.co, grp.group

REASON = "Costo sproporzionato rispetto al beneficio atteso"


@pytest.fixture(autouse=True)
def _media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)


def _finding(client, prep_id, ftype="opportunity", **extra):
    resp = client.post(URL_FINDINGS, {
        "audit_prep": prep_id, "finding_type": ftype, "title": f"Rilievo {ftype}", "description": "d",
        "audit_date": "2026-09-10", **extra,
    }, format="json")
    assert resp.status_code == 201, resp.data
    return resp.data


@pytest.mark.django_db
def test_not_pursue_with_reason_and_uploaded_proof_archives_pdca(client, prep):
    from apps.audit_prep.models import AuditFinding
    data = _finding(client, prep["id"])
    client.post(f"{URL_FINDINGS}{data['id']}/open-pdca/", {}, format="json")
    resp = client.post(f"{URL_FINDINGS}{data['id']}/not-pursue/",
                       {"reason": REASON, "file": _pdf()}, format="multipart")
    assert resp.status_code == 200, resp.data
    f = AuditFinding.objects.select_related("pdca_cycle", "closure_evidence").get(pk=data["id"])
    assert f.status == "not_pursued" and f.closure_notes == REASON
    assert f.closure_evidence is not None and f.closed_by_id
    assert f.pdca_cycle.fase_corrente == "archiviato" and f.pdca_cycle.motivo_archiviazione == REASON
    assert resp.data["not_pursued"]["pdca_archived"] == [f.pdca_cycle.title]
    assert f.is_overdue is False


@pytest.mark.django_db
def test_reason_required_proof_optional(client, prep):
    data = _finding(client, prep["id"], "observation")
    url = f"{URL_FINDINGS}{data['id']}/not-pursue/"
    assert client.post(url, {"reason": "corto"}, format="json").status_code == 400
    resp = client.post(url, {"reason": REASON}, format="json")
    assert resp.status_code == 200 and resp.data["status"] == "not_pursued"
    assert resp.data["closure_evidence"] is None


@pytest.mark.django_db
def test_nonconformity_cannot_be_not_pursued(client, prep):
    data = _finding(client, prep["id"], "minor_nc")
    resp = client.post(f"{URL_FINDINGS}{data['id']}/not-pursue/", {"reason": REASON}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_common_finding_not_pursued_on_all_sites(co, group):
    from apps.audit_prep.models import AuditFinding
    c = grp._client(co)
    data = _finding(c, group["preps"][0]["id"], apply_to_group=True)
    resp = c.post(f"{URL_FINDINGS}{data['id']}/not-pursue/", {"reason": REASON}, format="json")
    assert resp.status_code == 200, resp.data
    assert sorted(resp.data["not_pursued"]["sites"]) == ["TA", "TB"]
    assert set(AuditFinding.objects.filter(common_key__isnull=False).values_list("status", flat=True)) == {
        "not_pursued"}


@pytest.mark.django_db
def test_reopen(client, prep):
    data = _finding(client, prep["id"])
    client.post(f"{URL_FINDINGS}{data['id']}/open-pdca/", {}, format="json")
    client.post(f"{URL_FINDINGS}{data['id']}/not-pursue/", {"reason": REASON}, format="json")
    url = f"{URL_FINDINGS}{data['id']}/reopen/"
    assert client.post(url, {"reason": "x"}, format="json").status_code == 400
    resp = client.post(url, {"reason": "Opportunità ripresa nel budget 2027"}, format="json")
    assert resp.status_code == 200, resp.data
    assert resp.data["status"] == "open" and resp.data["closure_notes"] == ""
    assert resp.data["pdca_cycle"] is None  # l'archiviato non si riprende


@pytest.mark.django_db
def test_not_pursued_cannot_be_closed_and_is_not_open(client, prep, plant):
    from apps.management_review.services.snapshot import _audit_block
    data = _finding(client, prep["id"])
    client.post(f"{URL_FINDINGS}{data['id']}/not-pursue/", {"reason": REASON}, format="json")
    r = client.post(f"{URL_FINDINGS}{data['id']}/close/", {"closure_notes": "chiusura qualsiasi"}, format="json")
    assert r.status_code == 400
    block = _audit_block({"plant_id": plant.id}, timezone.localdate(),
                         timezone.now() - datetime.timedelta(days=365))
    assert block["opportunita_aperte"] == 0
    assert block["finding_non_perseguiti_12m"] == 1
    assert block["elenco_non_perseguiti"][0]["motivo"] == REASON

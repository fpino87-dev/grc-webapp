"""Correzione dei testi di un finding già salvato (refusi): titolo e
descrizione, anche sui finding comuni degli altri siti."""
import pytest

from . import test_audit_group as grp
from . import test_external_audit as ext
from .test_external_audit import URL_FINDINGS

user, client, plant = ext.user, ext.client, ext.plant
plants, tisax, co, group = grp.plants, grp.tisax, grp.co, grp.group


@pytest.fixture
def finding(client, plant):
    from apps.audit_prep.models import AuditFinding, AuditPrep
    prep = AuditPrep.objects.create(plant=plant, title="Audit", coverage_type="full")
    resp = client.post(URL_FINDINGS, {
        "audit_prep": str(prep.pk), "finding_type": "minor_nc", "title": "Titlo sbagliato",
        "description": "Descrizone", "audit_date": "2026-09-10",
    }, format="json")
    assert resp.status_code == 201, resp.data
    return AuditFinding.objects.get(pk=resp.data["id"])


@pytest.mark.django_db
def test_title_and_description_editable(client, finding):
    from core.audit import AuditLog
    resp = client.patch(f"{URL_FINDINGS}{finding.pk}/", {"title": "Titolo giusto", "description": "Descrizione"},
                        format="json")
    assert resp.status_code == 200, resp.data
    finding.refresh_from_db()
    assert (finding.title, finding.description) == ("Titolo giusto", "Descrizione")
    assert AuditLog.objects.filter(action_code="audit.finding.updated", entity_id=finding.pk).exists()


@pytest.mark.django_db
def test_other_fields_not_editable(client, finding):
    resp = client.patch(f"{URL_FINDINGS}{finding.pk}/", {"finding_type": "major_nc"}, format="json")
    assert resp.status_code == 400
    resp = client.patch(f"{URL_FINDINGS}{finding.pk}/", {"title": "  "}, format="json")
    assert resp.status_code == 400
    finding.refresh_from_db()
    assert finding.finding_type == "minor_nc" and finding.title == "Titlo sbagliato"


@pytest.mark.django_db
def test_archived_audit_findings_not_editable(client, finding):
    finding.audit_prep.status = "archiviato"
    finding.audit_prep.save()
    resp = client.patch(f"{URL_FINDINGS}{finding.pk}/", {"title": "Nuovo"}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_common_finding_text_propagates_to_sites(co, group, plants):
    from apps.audit_prep.models import AuditFinding
    c = grp._client(co)
    resp = c.post(URL_FINDINGS, {
        "audit_prep": group["preps"][0]["id"], "finding_type": "observation", "title": "Refuso",
        "description": "d", "audit_date": "2026-10-05", "apply_to_group": True,
    }, format="json")
    resp = c.patch(f"{URL_FINDINGS}{resp.data['id']}/", {"title": "Corretto", "root_cause": "Solo TA"},
                   format="json")
    assert resp.status_code == 200, resp.data
    rows = {f.audit_prep.plant.code: f for f in AuditFinding.objects.filter(common_key__isnull=False)
            .select_related("audit_prep__plant")}
    assert {f.title for f in rows.values()} == {"Corretto"}
    assert rows["TA"].root_cause == "Solo TA" and rows["TB"].root_cause == ""


@pytest.mark.django_db
def test_common_finding_text_needs_all_sites(co, group, plants):
    from apps.auth_grc.models import GrcRole
    c = grp._client(co)
    resp = c.post(URL_FINDINGS, {
        "audit_prep": group["preps"][0]["id"], "finding_type": "observation", "title": "Refuso",
        "description": "d", "audit_date": "2026-10-05", "apply_to_group": True,
    }, format="json")
    ta_only = grp._user("ta_only", GrcRole.COMPLIANCE_OFFICER, plants=[plants[0]])
    r = grp._client(ta_only).patch(f"{URL_FINDINGS}{resp.data['id']}/", {"title": "X"}, format="json")
    assert r.status_code == 403

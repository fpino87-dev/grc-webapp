"""Filtro origine dei PDCA per categoria e tipo di audit dei PDCA collegati
che segue il tipo dell'audit."""
import pytest

from . import test_audit_group as grp
from . import test_external_audit as ext
from .test_external_audit import URL_FINDINGS, URL_PREPS

user, client, plant, prep = ext.user, ext.client, ext.plant, ext.prep
plants, tisax, co, group = grp.plants, grp.tisax, grp.co, grp.group

URL_CYCLES = "/api/v1/pdca/cycles/"


@pytest.mark.django_db
def test_trigger_filter_groups_codes(client, plant):
    from apps.pdca.services import create_cycle
    for code in ("audit", "finding_observation", "incidente", "incident", "bcp_rto_sforato", "manual"):
        create_cycle(plant=plant, title=code, trigger_type=code)

    def titles(trigger):
        return sorted(r["title"] for r in client.get(URL_CYCLES, {"trigger_type": trigger}).data["results"])

    assert titles("audit") == ["audit", "finding_observation"]
    assert titles("incident") == ["incident", "incidente"]
    assert titles("bcp") == ["bcp_rto_sforato"]
    assert titles("manual") == ["manual"]
    assert titles("finding_observation") == ["finding_observation"]


@pytest.mark.django_db
def test_changing_audit_type_updates_linked_pdca(client, prep):
    from apps.audit_prep.models import AuditFinding
    resp = client.post(URL_FINDINGS, {
        "audit_prep": prep["id"], "finding_type": "minor_nc", "title": "NC", "description": "d",
        "audit_date": "2026-09-10",
    }, format="json")
    cycle = AuditFinding.objects.get(pk=resp.data["id"]).pdca_cycle
    assert cycle.audit_subtype == "seconda_parte"
    r = client.patch(f"{URL_PREPS}{prep['id']}/", {"audit_type": "interno", "external_consultant": True},
                     format="json")
    assert r.status_code == 200, r.data
    cycle.refresh_from_db()
    assert cycle.audit_subtype == "interno"


@pytest.mark.django_db
def test_changing_group_audit_type_updates_common_pdca(co, group):
    from apps.audit_prep.models import AuditFinding
    c = grp._client(co)
    c.post(URL_FINDINGS, {
        "audit_prep": group["preps"][0]["id"], "finding_type": "minor_nc", "title": "Comune", "description": "d",
        "audit_date": "2026-10-05", "apply_to_group": True, "common_pdca": True,
    }, format="json")
    cycle = AuditFinding.objects.filter(title="Comune").first().pdca_cycle
    assert cycle.audit_subtype == "terza_parte"
    r = c.patch(f"{grp.URL_GROUPS}{group['id']}/", {"audit_type": "seconda_parte"}, format="json")
    assert r.status_code == 200, r.data
    cycle.refresh_from_db()
    assert cycle.audit_subtype == "seconda_parte"


@pytest.mark.django_db
def test_search_matches_cycle_and_linked_finding(client, prep):
    from apps.pdca.services import create_cycle
    client.post(URL_FINDINGS, {
        "audit_prep": prep["id"], "finding_type": "minor_nc", "title": "Sospensione badge", "description": "d",
        "audit_date": "2026-09-10",
    }, format="json")
    create_cycle(plant=None, title="Ciclo senza finding", trigger_type="manual")
    rows = client.get(URL_CYCLES, {"search": "badge"}).data["results"]
    assert len(rows) == 1 and "badge" in rows[0]["title"]
    rows = client.get(URL_CYCLES, {"search": "Audit cliente OEM"}).data["results"]
    assert len(rows) == 1

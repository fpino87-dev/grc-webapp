"""PDCA di organizzazione per i rilievi comuni di un audit multi-sito: un solo
ciclo (senza sito) collegato ai finding con lo stesso common_key su tutti i
siti; gestione solo con scope org."""
import pytest
from django.utils import timezone

from . import test_audit_group as base
from .test_audit_group import URL_FINDINGS, _client, _user

# fixture dell'audit multi-sito riusate (gruppo TA+TB, compliance officer org)
plants, tisax, co, group = base.plants, base.tisax, base.co, base.group


def _common_nc(user, prep_id, common_pdca=False, title="Classificazione informazioni"):
    resp = _client(user).post(URL_FINDINGS, {
        "audit_prep": prep_id, "finding_type": "minor_nc", "title": title,
        "description": "Schema non applicato", "audit_date": "2026-10-05",
        "apply_to_group": True, "common_pdca": common_pdca,
    }, format="json")
    return resp


def _findings(title="Classificazione informazioni"):
    from apps.audit_prep.models import AuditFinding
    return list(AuditFinding.objects.filter(title=title).select_related("pdca_cycle", "audit_prep__plant"))


@pytest.mark.django_db
def test_common_nc_with_common_pdca_opens_one_org_cycle(co, group):
    from apps.pdca.models import PdcaCycle
    resp = _common_nc(co, group["preps"][0]["id"], common_pdca=True)
    assert resp.status_code == 201, resp.data
    findings = _findings()
    assert len(findings) == 2
    cycles = {f.pdca_cycle_id for f in findings}
    assert len(cycles) == 1
    cycle = PdcaCycle.objects.get(pk=cycles.pop())
    assert cycle.plant_id is None and cycle.audit_subtype == "terza_parte"
    # nessun PDCA di sito aperto in automatico
    assert not PdcaCycle.objects.filter(plant__isnull=False).exists()
    assert resp.data["pdca_is_org"] is True


@pytest.mark.django_db
def test_common_pdca_requires_org_scope(group, plants):
    from apps.auth_grc.models import GrcRole
    site_user = _user("two_sites", GrcRole.COMPLIANCE_OFFICER, plants=list(plants[:2]))
    resp = _common_nc(site_user, group["preps"][0]["id"], common_pdca=True)
    assert resp.status_code == 400
    assert _findings() == []


@pytest.mark.django_db
def test_open_common_pdca_replaces_untouched_auto_cycles(co, group):
    _common_nc(co, group["preps"][0]["id"])
    findings = _findings()
    old = {f.pdca_cycle for f in findings}
    assert all(c.plant_id for c in old)
    resp = _client(co).post(f"{URL_FINDINGS}{findings[0].pk}/open-common-pdca/", {}, format="json")
    assert resp.status_code == 201, resp.data
    assert sorted(resp.data["common_link"]["linked"]) == ["TA", "TB"]
    assert resp.data["common_link"]["skipped"] == []
    findings = _findings()
    assert len({f.pdca_cycle_id for f in findings}) == 1
    assert findings[0].pdca_cycle.plant_id is None
    for c in old:
        c.refresh_from_db()
        assert c.fase_corrente == "archiviato"


@pytest.mark.django_db
def test_worked_site_cycle_is_skipped(co, group):
    from apps.pdca.services import advance_phase
    _common_nc(co, group["preps"][0]["id"])
    f_ta, f_tb = sorted(_findings(), key=lambda f: f.audit_prep.plant.code)
    advance_phase(f_tb.pdca_cycle, co, phase_notes="Azione pianificata specifica per il sito TB")
    resp = _client(co).post(f"{URL_FINDINGS}{f_ta.pk}/open-common-pdca/", {}, format="json")
    assert resp.status_code == 201, resp.data
    assert resp.data["common_link"] == {"linked": ["TA"], "skipped": ["TB"]}
    f_tb.refresh_from_db()
    assert f_tb.pdca_cycle.plant_id is not None


@pytest.mark.django_db
def test_org_cycle_rejects_non_common_or_other_common_finding(co, group):
    from apps.audit_prep.models import AuditFinding
    _common_nc(co, group["preps"][0]["id"], common_pdca=True)
    cycle = _findings()[0].pdca_cycle
    # rilievo solo di sito
    resp = _client(co).post(URL_FINDINGS, {
        "audit_prep": group["preps"][1]["id"], "finding_type": "observation", "title": "Solo TB",
        "description": "d", "audit_date": "2026-10-05",
    }, format="json")
    solo = AuditFinding.objects.get(pk=resp.data["id"])
    r = _client(co).post(f"{URL_FINDINGS}{solo.pk}/link-pdca/", {"pdca_cycle": str(cycle.pk)}, format="json")
    assert r.status_code == 400
    # altro rilievo comune
    _client(co).post(URL_FINDINGS, {
        "audit_prep": group["preps"][0]["id"], "finding_type": "observation", "title": "Altro comune",
        "description": "d", "audit_date": "2026-10-05", "apply_to_group": True,
    }, format="json")
    other = _findings("Altro comune")[0]
    r = _client(co).post(f"{URL_FINDINGS}{other.pk}/link-pdca/", {"pdca_cycle": str(cycle.pk)}, format="json")
    assert r.status_code == 400


@pytest.mark.django_db
def test_link_existing_org_cycle_links_all_sites(co, group):
    from apps.pdca.services import create_cycle
    _client(co).post(URL_FINDINGS, {
        "audit_prep": group["preps"][0]["id"], "finding_type": "observation", "title": "Oss comune",
        "description": "d", "audit_date": "2026-10-05", "apply_to_group": True,
    }, format="json")
    cycle = create_cycle(plant=None, title="Azione di gruppo", trigger_type="audit", scope_type="org")
    f = _findings("Oss comune")[0]
    r = _client(co).post(f"{URL_FINDINGS}{f.pk}/link-pdca/", {"pdca_cycle": str(cycle.pk)}, format="json")
    assert r.status_code == 200, r.data
    assert {x.pdca_cycle_id for x in _findings("Oss comune")} == {cycle.pk}


@pytest.mark.django_db
def test_closing_org_cycle_closes_findings_on_all_sites(co, group):
    from apps.documents.models import Evidence
    from apps.pdca.services import advance_phase, close_cycle
    _common_nc(co, group["preps"][0]["id"], common_pdca=True)
    cycle = _findings()[0].pdca_cycle
    ev = Evidence.objects.create(
        title="Procedura classificazione", evidence_type="altro", plant=None,
        valid_until=timezone.localdate() + timezone.timedelta(days=365),
    )
    advance_phase(cycle, co, phase_notes="Piano: nuova procedura di classificazione di gruppo")
    advance_phase(cycle, co, phase_notes="Procedura emessa e diffusa", evidence=ev)
    advance_phase(cycle, co, phase_notes="Verifica efficacia positiva", outcome="ok")
    close_cycle(cycle, co, act_description="Procedura standardizzata su tutti i siti")
    assert {f.status for f in _findings()} == {"closed"}


@pytest.mark.django_db
def test_pdca_list_groups_common_findings_by_site(co, group):
    _common_nc(co, group["preps"][0]["id"], common_pdca=True)
    cycle = _findings()[0].pdca_cycle
    resp = _client(co).get(f"/api/v1/pdca/cycles/{cycle.pk}/")
    assert resp.status_code == 200
    rows = resp.data["findings"]
    assert sorted(r["plant_code"] for r in rows) == ["TA", "TB"]
    assert len({r["common_key"] for r in rows}) == 1 and rows[0]["common_key"]
    assert {r["group_title"] for r in rows} == {"TISAX AL2 2026"}

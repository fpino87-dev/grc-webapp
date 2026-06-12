"""
Security review 2026-06-12 — guard di accesso per plant e ruoli.

Vuln 1: eligible-owners leggibile da ruoli read-only (external_auditor) e per
        qualsiasi plant → ora ruoli write + check accesso plant.
Vuln 2/3: gap-analysis / export / audit-package restituivano la postura di
        compliance di QUALSIASI plant (e l'aggregato di tutti i siti) → ora
        user_can_access_plant + aggregato solo per scope org.
Vuln 4: link-document / link_evidence / PATCH M2M accettavano documenti ed
        evidenze di un ALTRO plant → ora perimetro stesso-plant/org-wide/shared.
Vuln 5: bulk-approve-soa firmabile da control_owner → ora SoAApprovalPermission.
"""
import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.auth_grc.models import GrcRole, UserPlantAccess
from apps.controls.models import Control, ControlInstance, Framework
from apps.documents.models import Document, Evidence
from apps.plants.models import Plant, PlantFramework

User = get_user_model()

URL = "/api/v1/controls/"


def make_user(username, role, scope_type="org", plants=()):
    u = User.objects.create_user(username=username, email=f"{username}@test.com", password="x")
    access = UserPlantAccess.objects.create(user=u, role=role, scope_type=scope_type)
    for p in plants:
        access.scope_plants.add(p)
    return u


def client_for(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def env(db):
    plant_a = Plant.objects.create(code="SEC-A", name="Plant A", country="IT",
                                   nis2_scope="importante", status="attivo")
    plant_b = Plant.objects.create(code="SEC-B", name="Plant B", country="IT",
                                   nis2_scope="importante", status="attivo")
    fw = Framework.objects.create(code="ISO27001", name="ISO", version="2022",
                                  published_at=timezone.localdate())
    ctrl = Control.objects.create(framework=fw, external_id="A.5.1",
                                  translations={"it": {"title": "Politiche"}},
                                  evidence_requirement={})
    # Senza PlantFramework attivo l'istanza è esclusa dal queryset del viewset
    # (filtro Exists(assigned)) e le azioni detail darebbero 404 spurî.
    PlantFramework.objects.create(plant=plant_a, framework=fw,
                                  active_from=timezone.localdate(), level="L2", active=True)
    inst_a = ControlInstance.objects.create(plant=plant_a, control=ctrl, status="non_valutato")
    return {"plant_a": plant_a, "plant_b": plant_b, "fw": fw, "ctrl": ctrl, "inst_a": inst_a}


# ── Vuln 1: eligible-owners ──────────────────────────────────────────────────

@pytest.mark.django_db
def test_eligible_owners_denied_to_external_auditor(env):
    auditor = make_user("ext_aud", GrcRole.EXTERNAL_AUDITOR, "single_plant", [env["plant_a"]])
    resp = client_for(auditor).get(f"{URL}instances/eligible-owners/", {"plant": str(env["plant_a"].id)})
    assert resp.status_code == 403  # ruolo read-only: niente elenco personale


@pytest.mark.django_db
def test_eligible_owners_denied_cross_plant(env):
    co = make_user("co_b", GrcRole.CONTROL_OWNER, "single_plant", [env["plant_b"]])
    resp = client_for(co).get(f"{URL}instances/eligible-owners/", {"plant": str(env["plant_a"].id)})
    assert resp.status_code == 403  # ruolo write ma su un altro sito


@pytest.mark.django_db
def test_eligible_owners_allowed_for_scoped_writer(env):
    co = make_user("co_a", GrcRole.CONTROL_OWNER, "single_plant", [env["plant_a"]])
    resp = client_for(co).get(f"{URL}instances/eligible-owners/", {"plant": str(env["plant_a"].id)})
    assert resp.status_code == 200


# ── Vuln 2/3: gap-analysis / export / audit-package ─────────────────────────

@pytest.mark.django_db
def test_gap_analysis_denied_cross_plant(env):
    pm = make_user("pm_b", GrcRole.PLANT_MANAGER, "single_plant", [env["plant_b"]])
    resp = client_for(pm).get(f"{URL}gap-analysis/", {"target": "ISO27001", "plant": str(env["plant_a"].id)})
    assert resp.status_code == 403


@pytest.mark.django_db
def test_gap_analysis_allowed_same_plant(env):
    pm = make_user("pm_a", GrcRole.PLANT_MANAGER, "single_plant", [env["plant_a"]])
    resp = client_for(pm).get(f"{URL}gap-analysis/", {"target": "ISO27001", "plant": str(env["plant_a"].id)})
    assert resp.status_code == 200


@pytest.mark.django_db
def test_export_denied_cross_plant_and_aggregate(env):
    pm = make_user("pm_b2", GrcRole.PLANT_MANAGER, "single_plant", [env["plant_b"]])
    c = client_for(pm)
    resp = c.get(f"{URL}export/", {"framework": "ISO27001", "fmt": "soa", "plant": str(env["plant_a"].id)})
    assert resp.status_code == 403
    # senza plant = aggregato su tutti i siti → vietato a chi non ha scope org
    resp = c.get(f"{URL}export/", {"framework": "ISO27001", "fmt": "soa"})
    assert resp.status_code == 403


@pytest.mark.django_db
def test_audit_package_denied_cross_plant_and_aggregate(env):
    pm = make_user("pm_b3", GrcRole.PLANT_MANAGER, "single_plant", [env["plant_b"]])
    c = client_for(pm)
    resp = c.get(f"{URL}audit-package/", {"framework": "ISO27001", "plant": str(env["plant_a"].id)})
    assert resp.status_code == 403
    resp = c.get(f"{URL}audit-package/", {"framework": "ISO27001"})
    assert resp.status_code == 403


# ── Vuln 4: cross-plant document/evidence linking ────────────────────────────

@pytest.fixture
def writer_a(env):
    return make_user("writer_a", GrcRole.COMPLIANCE_OFFICER, "org")


@pytest.mark.django_db
def test_link_document_rejects_other_plant(env, writer_a):
    doc_b = Document.objects.create(title="Doc B", document_type="policy",
                                    plant=env["plant_b"], created_by=writer_a)
    resp = client_for(writer_a).post(
        f"{URL}instances/{env['inst_a'].id}/link-document/",
        {"document_id": str(doc_b.id)}, format="json",
    )
    assert resp.status_code == 404
    assert env["inst_a"].documents.count() == 0


@pytest.mark.django_db
def test_link_document_accepts_same_plant_and_shared(env, writer_a):
    c = client_for(writer_a)
    doc_a = Document.objects.create(title="Doc A", document_type="policy",
                                    plant=env["plant_a"], created_by=writer_a)
    doc_shared = Document.objects.create(title="Doc B shared", document_type="policy",
                                         plant=env["plant_b"], created_by=writer_a)
    doc_shared.shared_plants.add(env["plant_a"])
    for doc in (doc_a, doc_shared):
        resp = c.post(f"{URL}instances/{env['inst_a'].id}/link-document/",
                      {"document_id": str(doc.id)}, format="json")
        assert resp.status_code == 200
    assert env["inst_a"].documents.count() == 2


@pytest.mark.django_db
def test_link_evidence_rejects_other_plant(env, writer_a):
    ev_b = Evidence.objects.create(title="Ev B", evidence_type="report",
                                   plant=env["plant_b"], created_by=writer_a)
    resp = client_for(writer_a).post(
        f"{URL}instances/{env['inst_a'].id}/link_evidence/",
        {"evidence_id": str(ev_b.id)}, format="json",
    )
    assert resp.status_code == 404
    assert env["inst_a"].evidences.count() == 0


@pytest.mark.django_db
def test_patch_m2m_rejects_other_plant_evidences(env, writer_a):
    c = client_for(writer_a)
    ev_b = Evidence.objects.create(title="Ev B", evidence_type="report",
                                   plant=env["plant_b"], created_by=writer_a)
    resp = c.patch(f"{URL}instances/{env['inst_a'].id}/",
                   {"evidences": [str(ev_b.id)]}, format="json")
    assert resp.status_code == 400
    assert env["inst_a"].evidences.count() == 0


@pytest.mark.django_db
def test_patch_documents_is_inert(env, writer_a):
    """'documents' è un M2M reverse (Document.control_refs): non è un campo del
    serializer e la PATCH lo ignora — il solo canale è link-document (guardato)."""
    doc_b = Document.objects.create(title="Doc B", document_type="policy",
                                    plant=env["plant_b"], created_by=writer_a)
    resp = client_for(writer_a).patch(f"{URL}instances/{env['inst_a'].id}/",
                                      {"documents": [str(doc_b.id)]}, format="json")
    assert resp.status_code == 200
    assert env["inst_a"].documents.count() == 0  # ignorato, nessun collegamento


# ── Vuln 5: SoA approval riservata alla governance ───────────────────────────

@pytest.mark.django_db
def test_bulk_approve_soa_denied_to_control_owner(env):
    co = make_user("co_soa", GrcRole.CONTROL_OWNER, "single_plant", [env["plant_a"]])
    resp = client_for(co).post(
        f"{URL}instances/bulk-approve-soa/",
        {"instance_ids": [str(env["inst_a"].id)], "approved": True}, format="json",
    )
    assert resp.status_code == 403
    env["inst_a"].refresh_from_db()
    assert env["inst_a"].approved_in_soa is False


@pytest.mark.django_db
def test_bulk_approve_soa_allowed_to_compliance_officer(env):
    co = make_user("comp_off", GrcRole.COMPLIANCE_OFFICER, "org")
    resp = client_for(co).post(
        f"{URL}instances/bulk-approve-soa/",
        {"instance_ids": [str(env["inst_a"].id)], "approved": True}, format="json",
    )
    assert resp.status_code == 200
    env["inst_a"].refresh_from_db()
    assert env["inst_a"].approved_in_soa is True

"""
Test dell'espansione gerarchica TISAX nell'AuditPrep:

- L3 (e PROTO) deve coprire automaticamente L2 nel seeding e nel sync.
- L'auto-validation segnala un warning se il prep e' L3/PROTO ma mancano
  EvidenceItem dei livelli inferiori.
"""
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_PREPS = "/api/v1/audit-prep/audit-preps/"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(
        username="fwexp", email="fwexp@test.com", password="x",
    )
    UserPlantAccess.objects.create(
        user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org",
    )
    return u


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="FWEXP", name="Plant FWEXP", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def tisax_l2(db):
    from apps.controls.models import Framework
    return Framework.objects.create(
        code="TISAX_L2", name="TISAX AL2", version="6.0",
        published_at=date.today(),
    )


@pytest.fixture
def tisax_l3(db):
    from apps.controls.models import Framework
    return Framework.objects.create(
        code="TISAX_L3", name="TISAX AL3", version="6.0",
        published_at=date.today(),
    )


def _make_control(plant, fw, code: str, title: str = "Ctrl"):
    """Crea un Control + ControlInstance per il plant dato."""
    from apps.controls.models import Control, ControlDomain, ControlInstance
    dom, _ = ControlDomain.objects.get_or_create(
        framework=fw, code=f"DOM-{fw.code}",
        defaults={"translations": {"it": {"name": f"Dom {fw.code}"}}, "order": 1},
    )
    ctrl = Control.objects.create(
        framework=fw, domain=dom, external_id=code,
        translations={"it": {"name": title, "description": "—"}},
        level=("L3" if fw.code == "TISAX_L3" else "L2"),
        evidence_requirement={}, control_category="technical",
    )
    return ControlInstance.objects.create(
        plant=plant, control=ctrl, status="non_valutato",
    )


# ---------------------------------------------------------------------------
# Unit: expand_tisax
# ---------------------------------------------------------------------------

def test_expand_tisax_l3_implies_l2():
    from apps.audit_prep.framework_hierarchy import expand_tisax
    assert expand_tisax(["TISAX_L3"]) == ["TISAX_L2", "TISAX_L3"]


def test_expand_tisax_proto_implies_l2_and_l3():
    from apps.audit_prep.framework_hierarchy import expand_tisax
    assert expand_tisax(["TISAX_PROTO"]) == ["TISAX_L2", "TISAX_L3", "TISAX_PROTO"]


def test_expand_tisax_keeps_non_tisax_unchanged():
    from apps.audit_prep.framework_hierarchy import expand_tisax
    assert expand_tisax(["ISO27001"]) == ["ISO27001"]
    assert expand_tisax([]) == []
    assert expand_tisax(None) == []


# ---------------------------------------------------------------------------
# Seeding manuale (perform_create) e sync
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_create_prep_l3_auto_seeds_l2_and_l3_items(client, plant, tisax_l2, tisax_l3, user):
    """Creando un prep manuale con framework=TISAX_L3, gli EvidenceItem
    devono essere seedati per entrambi i livelli (L2 estesa da L3)."""
    from apps.audit_prep.models import AuditPrep
    _make_control(plant, tisax_l2, "ISA-1.1.1", "L2-A")
    _make_control(plant, tisax_l2, "ISA-1.1.2", "L2-B")
    _make_control(plant, tisax_l3, "ISA-1.1.1-VH", "L3-A")

    payload = {
        "plant": str(plant.id),
        "framework": str(tisax_l3.id),
        "title": "Audit TISAX L3",
        "audit_date": str(date.today()),
        "status": "in_corso",
        "coverage_type": "full",
    }
    resp = client.post(URL_PREPS, payload, format="json")
    assert resp.status_code == 201, resp.json()

    prep = AuditPrep.objects.get(pk=resp.json()["id"])
    fw_codes = list(
        prep.evidence_items.values_list(
            "control_instance__control__framework__code", flat=True,
        )
    )
    assert sorted(set(fw_codes)) == ["TISAX_L2", "TISAX_L3"]
    assert prep.evidence_items.count() == 3


@pytest.mark.django_db
def test_create_prep_iso_does_not_auto_seed(client, plant, user):
    """Un framework non gerarchico non triggera il seed automatico:
    il flusso manuale resta intatto."""
    from apps.controls.models import Framework
    from apps.audit_prep.models import AuditPrep
    iso = Framework.objects.create(
        code="ISO27001-X", name="ISO", version="2022", published_at=date.today(),
    )
    _make_control(plant, iso, "A.5.1")

    payload = {
        "plant": str(plant.id),
        "framework": str(iso.id),
        "title": "Audit ISO",
        "audit_date": str(date.today()),
        "status": "in_corso",
    }
    resp = client.post(URL_PREPS, payload, format="json")
    assert resp.status_code == 201
    prep = AuditPrep.objects.get(pk=resp.json()["id"])
    assert prep.evidence_items.count() == 0


@pytest.mark.django_db
def test_sync_controls_adds_missing_l2_items(client, plant, tisax_l2, tisax_l3, user):
    """Prep L3 creato senza L2 (es. legacy) -> sync-controls aggiunge gli
    EvidenceItem mancanti e l'azione e' idempotente."""
    from apps.audit_prep.models import AuditPrep, EvidenceItem

    l2_a = _make_control(plant, tisax_l2, "ISA-2.1.1", "L2-A")
    _make_control(plant, tisax_l2, "ISA-2.1.2", "L2-B")
    l3_a = _make_control(plant, tisax_l3, "ISA-2.1.1-VH", "L3-A")

    prep = AuditPrep.objects.create(
        plant=plant, framework=tisax_l3,
        title="Legacy L3 prep",
        audit_date=date.today(), status="in_corso",
        coverage_type="full", created_by=user,
    )
    # Stato pre-fix: contiene solo i controlli L3
    EvidenceItem.objects.create(
        audit_prep=prep, control_instance=l3_a,
        description="L3-A", status="mancante", created_by=user,
    )
    assert prep.evidence_items.count() == 1

    r1 = client.post(f"{URL_PREPS}{prep.id}/sync-controls/", {}, format="json")
    assert r1.status_code == 200, r1.json()
    data = r1.json()
    assert data["added"] == 2
    assert data["frameworks_expanded"] == ["TISAX_L2", "TISAX_L3"]
    assert prep.evidence_items.count() == 3

    # Idempotenza: seconda chiamata non duplica.
    r2 = client.post(f"{URL_PREPS}{prep.id}/sync-controls/", {}, format="json")
    assert r2.status_code == 200
    assert r2.json()["added"] == 0
    assert prep.evidence_items.count() == 3


@pytest.mark.django_db
def test_sync_controls_noop_for_non_hierarchical_framework(client, plant, user):
    """Framework non TISAX -> nessuna espansione, payload chiarisce il no-op."""
    from apps.audit_prep.models import AuditPrep
    from apps.controls.models import Framework
    iso = Framework.objects.create(
        code="ISO27001-Y", name="ISO Y", version="2022", published_at=date.today(),
    )
    prep = AuditPrep.objects.create(
        plant=plant, framework=iso, title="ISO prep",
        audit_date=date.today(), status="in_corso", created_by=user,
    )
    resp = client.post(f"{URL_PREPS}{prep.id}/sync-controls/", {}, format="json")
    assert resp.status_code == 200
    assert resp.json()["added"] == 0
    assert resp.json()["frameworks_expanded"] == ["ISO27001-Y"]


@pytest.mark.django_db
def test_sync_controls_blocked_on_archived_prep(client, plant, tisax_l3, user):
    from apps.audit_prep.models import AuditPrep
    prep = AuditPrep.objects.create(
        plant=plant, framework=tisax_l3, title="Archived",
        audit_date=date.today(), status="archiviato", created_by=user,
    )
    resp = client.post(f"{URL_PREPS}{prep.id}/sync-controls/", {}, format="json")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# launch_audit_from_program
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_launch_audit_from_program_l3_creates_l2_and_l3_items(
    plant, tisax_l2, tisax_l3, user,
):
    """Audit lanciato dal programma con framework_codes=['TISAX_L3'] deve
    seedare EvidenceItem per L2+L3 (gerarchia espansa)."""
    from apps.audit_prep.models import AuditProgram
    from apps.audit_prep.services import launch_audit_from_program

    _make_control(plant, tisax_l2, "ISA-3.1.1", "L2-A")
    _make_control(plant, tisax_l2, "ISA-3.1.2", "L2-B")
    _make_control(plant, tisax_l3, "ISA-3.1.1-VH", "L3-A")

    program = AuditProgram.objects.create(
        plant=plant, framework=tisax_l3, year=2026,
        title="Programma 2026", status="approvato", created_by=user,
    )
    audit_entry = {
        "id": "audit-1", "quarter": 1,
        "title": "Audit Q1 TISAX L3",
        "framework_codes": ["TISAX_L3"],
        "coverage_type": "full",
        "scope_domains": [],
        "planned_date": str(date.today()),
        "auditor_name": "",
    }
    program.planned_audits = [audit_entry]
    program.save(update_fields=["planned_audits"])

    prep = launch_audit_from_program(program, audit_entry, user)
    assert prep.framework.code == "TISAX_L3"
    fw_codes = sorted(set(
        prep.evidence_items.values_list(
            "control_instance__control__framework__code", flat=True,
        )
    ))
    assert fw_codes == ["TISAX_L2", "TISAX_L3"]
    assert prep.evidence_items.count() == 3


# ---------------------------------------------------------------------------
# auto-validate warning
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_auto_validate_warns_when_l3_prep_missing_l2_items(
    client, plant, tisax_l2, tisax_l3, user,
):
    """Prep L3 senza EvidenceItem L2 -> warning informativo nel summary."""
    from apps.audit_prep.models import AuditPrep, EvidenceItem

    _make_control(plant, tisax_l2, "ISA-4.1.1", "L2-A")  # esiste ma non nel prep
    l3_a = _make_control(plant, tisax_l3, "ISA-4.1.1-VH", "L3-A")

    prep = AuditPrep.objects.create(
        plant=plant, framework=tisax_l3, title="L3 senza L2",
        audit_date=date.today(), status="in_corso", created_by=user,
    )
    EvidenceItem.objects.create(
        audit_prep=prep, control_instance=l3_a,
        description="L3-A", status="mancante", created_by=user,
    )

    resp = client.post(f"{URL_PREPS}{prep.id}/auto-validate/", {}, format="json")
    assert resp.status_code == 200
    data = resp.json()
    assert "warning" in data
    assert data["warning"]["code"] == "missing_extended_controls"
    assert "TISAX_L2" in data["warning"]["missing_frameworks"]


@pytest.mark.django_db
def test_auto_validate_l2_satisfied_by_l3_extends_evidence(
    client, plant, tisax_l2, tisax_l3, user,
):
    """L2 controllo esteso da un L3 con evidenza valida + documento approvato:
    auto-validate non deve aprire un finding (l'evidenza L3 copre L2)."""
    from datetime import timedelta
    from apps.audit_prep.models import AuditFinding, AuditPrep, EvidenceItem
    from apps.controls.models import ControlMapping
    from apps.documents.models import Document, Evidence

    l2_a = _make_control(plant, tisax_l2, "ISA-6.1.1", "L2-A")
    l3_a = _make_control(plant, tisax_l3, "ISA-6.1.1-VH", "L3-A")
    ControlMapping.objects.create(
        source_control=l3_a.control,
        target_control=l2_a.control,
        relationship="extends",
    )

    doc = Document.objects.create(
        plant=plant, title="Procedura X", status="approvato",
        category="procedura", document_type="procedura",
        expiry_date=date.today() + timedelta(days=365),
        created_by=user,
    )
    doc.control_refs.add(l3_a)

    ev = Evidence.objects.create(
        plant=plant, title="Screenshot config", evidence_type="screenshot",
        valid_until=date.today() + timedelta(days=180),
        uploaded_by=user, created_by=user,
    )
    ev.control_instances.add(l3_a)

    prep = AuditPrep.objects.create(
        plant=plant, framework=tisax_l3, title="Prep L3 con L2 esteso",
        audit_date=date.today(), status="in_corso", created_by=user,
    )
    EvidenceItem.objects.create(
        audit_prep=prep, control_instance=l2_a,
        description="L2-A", status="mancante", created_by=user,
    )
    EvidenceItem.objects.create(
        audit_prep=prep, control_instance=l3_a,
        description="L3-A", status="mancante", created_by=user,
    )

    resp = client.post(f"{URL_PREPS}{prep.id}/auto-validate/", {}, format="json")
    assert resp.status_code == 200, resp.json()
    data = resp.json()
    # Entrambi gli item devono risultare "presente": L3 coperto dalle proprie
    # evidenze, L2 coperto da quelle del controllo che lo estende.
    assert data["presente"] == 2, data
    assert data["mancante"] == 0, data
    # Nessun finding aperto (auto-generato) per gli item.
    findings = AuditFinding.objects.filter(audit_prep=prep)
    assert findings.count() == 0


@pytest.mark.django_db
def test_auto_validate_no_warning_when_l3_prep_includes_l2(
    client, plant, tisax_l2, tisax_l3, user,
):
    """Prep L3 che gia' contiene EvidenceItem L2 -> nessun warning."""
    from apps.audit_prep.models import AuditPrep, EvidenceItem

    l2_a = _make_control(plant, tisax_l2, "ISA-5.1.1", "L2-A")
    l3_a = _make_control(plant, tisax_l3, "ISA-5.1.1-VH", "L3-A")

    prep = AuditPrep.objects.create(
        plant=plant, framework=tisax_l3, title="L3 completo",
        audit_date=date.today(), status="in_corso", created_by=user,
    )
    EvidenceItem.objects.create(
        audit_prep=prep, control_instance=l2_a,
        description="L2-A", status="mancante", created_by=user,
    )
    EvidenceItem.objects.create(
        audit_prep=prep, control_instance=l3_a,
        description="L3-A", status="mancante", created_by=user,
    )

    resp = client.post(f"{URL_PREPS}{prep.id}/auto-validate/", {}, format="json")
    assert resp.status_code == 200
    data = resp.json()
    assert "warning" not in data

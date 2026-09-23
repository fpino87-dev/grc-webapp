"""
VDA ISA "Implementation description" dei controlli TISAX.

- scritta solo dall'endpoint dedicato (audit trail), non dalla PATCH generica;
- esportata nel VDA ISA (orizzontale) con i riferimenti documentali;
- advisor del Centro Operativo per ML ≥ 3 senza descrizione.
"""
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.controls.export_engine import generate_export

User = get_user_model()

URL_INSTANCES = "/api/v1/controls/instances/"


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="impl_user", email="impl@test.com", password="test")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
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
        code="IMPL-P", name="Impl Plant", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def fw_pair(db, plant):
    from apps.controls.models import Framework
    from apps.plants.models import PlantFramework
    fw_l2 = Framework.objects.create(
        code="TISAX_L2", name="TISAX L2", version="6.0", published_at=timezone.localdate(),
    )
    fw_l3 = Framework.objects.create(
        code="TISAX_L3", name="TISAX L3", version="6.0", published_at=timezone.localdate(),
    )
    for fw in (fw_l2, fw_l3):
        PlantFramework.objects.create(
            plant=plant, framework=fw, active_from=timezone.localdate(), level="AL3", active=True,
        )
    return fw_l2, fw_l3


def _instance(plant, fw, ext_id, **kwargs):
    from apps.controls.models import Control, ControlInstance
    ctrl = Control.objects.create(
        framework=fw, external_id=ext_id,
        translations={"en": {"title": f"Title {ext_id}"}}, level="L2",
    )
    return ControlInstance.objects.create(plant=plant, control=ctrl, **kwargs)


# --- endpoint ----------------------------------------------------------------

@pytest.mark.django_db
def test_set_implementation_saves_and_audits(client, plant, fw_pair):
    from core.audit import AuditLog
    inst = _instance(plant, fw_pair[0], "ISA-1.1.1")
    text = "Policy ISMS approvata dal CdA, revisione annuale gestita dall'ISM."
    resp = client.post(
        f"{URL_INSTANCES}{inst.id}/set-implementation/",
        {"implementation_description": f"  {text}  "}, format="json",
    )
    assert resp.status_code == 200
    inst.refresh_from_db()
    assert inst.implementation_description == text
    log = AuditLog.objects.get(entity_id=inst.pk, action_code="control.implementation_description_set")
    # il testo non finisce nel payload di audit, solo metadati
    assert log.payload == {"length": len(text), "cleared": False, "was_empty": True}

    detail = client.get(f"{URL_INSTANCES}{inst.id}/detail-info/")
    assert detail.data["implementation_description"] == text


@pytest.mark.django_db
def test_set_implementation_unchanged_does_not_audit(client, plant, fw_pair):
    from core.audit import AuditLog
    inst = _instance(plant, fw_pair[0], "ISA-1.1.2", implementation_description="Uguale")
    resp = client.post(
        f"{URL_INSTANCES}{inst.id}/set-implementation/",
        {"implementation_description": "Uguale"}, format="json",
    )
    assert resp.status_code == 200
    assert not AuditLog.objects.filter(
        entity_id=inst.pk, action_code="control.implementation_description_set"
    ).exists()


@pytest.mark.django_db
def test_set_implementation_too_long_rejected(client, plant, fw_pair):
    inst = _instance(plant, fw_pair[0], "ISA-1.1.3")
    resp = client.post(
        f"{URL_INSTANCES}{inst.id}/set-implementation/",
        {"implementation_description": "x" * 5001}, format="json",
    )
    assert resp.status_code == 400
    inst.refresh_from_db()
    assert inst.implementation_description == ""


@pytest.mark.django_db
def test_patch_cannot_write_implementation(client, plant, fw_pair):
    inst = _instance(plant, fw_pair[0], "ISA-1.1.4")
    resp = client.patch(
        f"{URL_INSTANCES}{inst.id}/", {"implementation_description": "bypass"}, format="json",
    )
    assert resp.status_code == 200
    inst.refresh_from_db()
    assert inst.implementation_description == ""


# --- export VDA ISA ----------------------------------------------------------

@pytest.mark.django_db
def test_vda_export_landscape_with_description_and_references(plant, fw_pair, user):
    from apps.documents.models import Document, Evidence
    inst = _instance(
        plant, fw_pair[0], "ISA-2.1.1", status="compliant",
        implementation_description="Riga 1\n<b>Riga 2</b>",
    )
    doc = Document.objects.create(
        title="Politica sicurezza", document_code="POL-001", category="policy",
        status="approvato", plant=plant,
    )
    doc.control_refs.add(inst)
    ev = Evidence.objects.create(
        title="Report scansione", evidence_type="altro", plant=plant,
        valid_until=timezone.localdate() + datetime.timedelta(days=30),
    )
    inst.evidences.add(ev)

    html = generate_export("TISAX_L2", plant.pk, "vda_isa", user)

    assert "size: A4 landscape" in html
    assert "<th>Implementation description</th>" in html
    assert "<th>Reference documentation</th>" in html
    row = html.split("<strong>ISA-2.1.1</strong>")[1].split("</tr>")[0]
    assert "Riga 1\n&lt;b&gt;Riga 2&lt;/b&gt;" in row  # escapata, a capo preservati
    assert "POL-001 Politica sicurezza" in row
    assert "[approvato]" not in row  # lo stato compare solo se non approvato
    assert "Report scansione (valida fino al" in row


@pytest.mark.django_db
def test_vda_export_flags_missing_description_for_ml3(plant, fw_pair, user):
    _instance(plant, fw_pair[0], "ISA-3.1.1", status="compliant")
    _instance(plant, fw_pair[0], "ISA-3.1.2", status="gap")

    html = generate_export("TISAX_L2", plant.pk, "vda_isa", user)

    row_ml3 = html.split("<strong>ISA-3.1.1</strong>")[1].split("</tr>")[0]
    row_gap = html.split("<strong>ISA-3.1.2</strong>")[1].split("</tr>")[0]
    assert "Missing" in row_ml3
    assert "Missing" not in row_gap
    assert "senza Implementation description</div>\n    <div class=\"meta-value\">1<" in html


@pytest.mark.django_db
def test_vda_export_l3_merge_description_falls_back_to_base(plant, fw_pair, user):
    fw_l2, fw_l3 = fw_pair
    _instance(plant, fw_l2, "ISA-4.1.1", implementation_description="Scritta sul base")
    _instance(plant, fw_l3, "ISA-4.1.1-VH", status="compliant")

    html = generate_export("TISAX_L3", plant.pk, "vda_isa", user)

    row = html.split("<strong>ISA-4.1.1</strong>")[1].split("</tr>")[0]
    assert "L2 + L3 (VH)" in row
    assert "Scritta sul base" in row


# --- advisor Centro Operativo ------------------------------------------------

@pytest.mark.django_db
def test_advisor_counts_ml3_without_description(plant, fw_pair):
    from apps.cockpit.advisors_builtin import controls_tisax_missing_implementation_advisor
    from apps.cockpit.insights import AdvisorContext
    fw_l2 = fw_pair[0]
    _instance(plant, fw_l2, "ISA-5.1.1", status="compliant")                      # conta
    _instance(plant, fw_l2, "ISA-5.1.2", status="compliant",
              implementation_description="Descritta")                           # no: descritta
    _instance(plant, fw_l2, "ISA-5.1.3", status="parziale")                       # no: ML 2
    _instance(plant, fw_l2, "ISA-5.1.4", status="gap",
              maturity_level=3, maturity_level_override=True)                    # conta: override
    _instance(plant, fw_l2, "ISA-5.1.5", status="compliant",
              maturity_level=2, maturity_level_override=True)                    # no: override 2

    out = controls_tisax_missing_implementation_advisor(AdvisorContext())
    matching = [i for i in out if i.plant_id == str(plant.pk)]
    assert len(matching) == 1
    assert matching[0].code == "controls.tisax_missing_implementation"
    assert matching[0].params["count"] == 2


@pytest.mark.django_db
def test_advisor_ignores_non_tisax(plant):
    from apps.controls.models import Framework
    from apps.plants.models import PlantFramework
    from apps.cockpit.advisors_builtin import controls_tisax_missing_implementation_advisor
    from apps.cockpit.insights import AdvisorContext
    iso = Framework.objects.create(
        code="ISO27001", name="ISO", version="2022", published_at=timezone.localdate(),
    )
    PlantFramework.objects.create(
        plant=plant, framework=iso, active_from=timezone.localdate(), level="L2", active=True,
    )
    _instance(plant, iso, "A.5.1", status="compliant")
    assert controls_tisax_missing_implementation_advisor(AdvisorContext()) == []

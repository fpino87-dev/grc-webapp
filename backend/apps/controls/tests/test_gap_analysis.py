"""
Test C12 — gap analysis cross-framework via hub ISO (SPEC_gap_analysis).

Verifica: profili ACN a livello requirement (87/116-like), credito di riuso
per relazione (equivalente/parziale, mai correlato), cross-link sempre
visibili anche con controparte non compliant (richiesta utente), transitività
via hub con gamba più debole, esclusioni (na / SoA), profili TISAX AL2/AL3.
"""
import pytest
from django.utils import timezone

from apps.controls.models import Control, ControlInstance, ControlMapping, Framework
from apps.controls.services.gap import run_gap_analysis
from apps.plants.models import Plant


@pytest.fixture
def plant(db):
    return Plant.objects.create(
        code="GAP-P", name="Plant Gap", country="IT",
        nis2_scope="importante", status="attivo",
    )


def _fw(code):
    return Framework.objects.create(
        code=code, name=code, version="1", published_at=timezone.localdate(),
    )


def _ctrl(fw, ext, requirements=None, level=""):
    return Control.objects.create(
        framework=fw, external_id=ext, level=level,
        translations={"it": {"title": f"Titolo {ext}"}},
        evidence_requirement={}, requirements=requirements or [],
    )


@pytest.fixture
def world(db, plant):
    """Mini-universo: hub ISO + ACN (con requirements) + NIS2 + TISAX L2/L3."""
    iso = _fw("ISO27001")
    acn = _fw("ACN_NIS2")
    nis2 = _fw("NIS2")
    l2 = _fw("TISAX_L2")
    l3 = _fw("TISAX_L3")

    iso_a = _ctrl(iso, "A.5.1")
    iso_b = _ctrl(iso, "A.8.24")

    req_both = {"punto": "1", "applies_to": ["important", "essential"],
                "translations": {"it": {"text": "Req comune"}}}
    req_ess = {"punto": "2", "applies_to": ["essential"],
               "translations": {"it": {"text": "Req solo essenziale"}}}
    acn_m1 = _ctrl(acn, "ACN-GV.PO-01", requirements=[req_both, req_ess])
    acn_m2 = _ctrl(acn, "ACN-PR.DS-01", requirements=[req_both])

    nis2_c = _ctrl(nis2, "NIS2-ART21-1.1")

    l2_c = _ctrl(l2, "ISA-1.1.1", level="L2")
    l3_c = _ctrl(l3, "ISA-1.1.1-VH", level="L3")

    ControlMapping.objects.create(source_control=iso_a, target_control=acn_m1, relationship="equivalente")
    ControlMapping.objects.create(source_control=iso_b, target_control=acn_m2, relationship="correlato")
    ControlMapping.objects.create(source_control=iso_a, target_control=nis2_c, relationship="parziale")
    ControlMapping.objects.create(source_control=iso_a, target_control=l2_c, relationship="equivalente")
    ControlMapping.objects.create(source_control=l3_c, target_control=l2_c, relationship="extends")

    return {
        "iso_a": iso_a, "iso_b": iso_b, "acn_m1": acn_m1, "acn_m2": acn_m2,
        "nis2_c": nis2_c, "l2_c": l2_c, "l3_c": l3_c,
    }


def _instance(plant, control, status, **kw):
    return ControlInstance.objects.create(plant=plant, control=control, status=status, **kw)


def _item(report, ext_id):
    return next(i for i in report["items"] if i["external_id"] == ext_id)


# ── Profili ACN (requirement-level) ──────────────────────────────────────────

@pytest.mark.django_db
def test_acn_profile_importante_filters_requirements(plant, world):
    report = run_gap_analysis("ACN_NIS2", plant, profile="importante")
    m1 = _item(report, "ACN-GV.PO-01")
    assert [r["punto"] for r in m1["requirements"]] == ["1"]  # solo req "important"
    assert m1["weight"] == 1
    # denominatore = requirement applicabili: 1 (m1) + 1 (m2)
    assert report["coverage"]["applicable"] == 2


@pytest.mark.django_db
def test_acn_profile_essenziale_counts_all_requirements(plant, world):
    report = run_gap_analysis("ACN_NIS2", plant, profile="essenziale")
    assert _item(report, "ACN-GV.PO-01")["weight"] == 2
    assert report["coverage"]["applicable"] == 3


@pytest.mark.django_db
def test_acn_profile_defaults_from_plant_scope(plant, world):
    # plant.nis2_scope == "importante" → profilo derivato
    report = run_gap_analysis("ACN_NIS2", plant)
    assert report["profile"] == "importante"


# ── Riuso cross-framework ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_equivalente_compliant_gives_coperto_riuso(plant, world):
    _instance(plant, world["iso_a"], "compliant")
    report = run_gap_analysis("ACN_NIS2", plant, profile="importante")
    m1 = _item(report, "ACN-GV.PO-01")
    assert m1["state"] == "coperto_riuso"
    iso_link = next(c for c in m1["cross"] if c["external_id"] == "A.5.1")
    assert iso_link["relationship"] == "equivalente"
    assert iso_link["status"] == "compliant"


@pytest.mark.django_db
def test_cross_link_visible_even_if_counterpart_not_compliant(plant, world):
    """Richiesta utente: il legame va mostrato comunque — 'se fosse ok
    potresti già essere compliant'."""
    _instance(plant, world["iso_a"], "gap")
    report = run_gap_analysis("ACN_NIS2", plant, profile="importante")
    m1 = _item(report, "ACN-GV.PO-01")
    assert m1["state"] == "scoperto"  # nessun credito
    iso_link = next(c for c in m1["cross"] if c["external_id"] == "A.5.1")
    assert iso_link["status"] == "gap"  # ma il cross-link c'è, con lo stato


@pytest.mark.django_db
def test_correlato_never_gives_credit(plant, world):
    _instance(plant, world["iso_b"], "compliant")
    report = run_gap_analysis("ACN_NIS2", plant, profile="importante")
    m2 = _item(report, "ACN-PR.DS-01")
    assert m2["state"] == "scoperto"
    assert any(c["relationship"] == "correlato" and c["status"] == "compliant"
               for c in m2["cross"])


@pytest.mark.django_db
def test_parziale_compliant_gives_parziale_riuso(plant, world):
    _instance(plant, world["iso_a"], "compliant")
    report = run_gap_analysis("NIS2", plant)
    c = _item(report, "NIS2-ART21-1.1")
    assert c["state"] == "parziale_riuso"


@pytest.mark.django_db
def test_transitivity_weakest_link_via_hub(plant, world):
    """NIS2 ← (parziale) ISO A.5.1 (equivalente) → TISAX ISA-1.1.1 compliant:
    la controparte TISAX appare con relazione 'parziale' (gamba più debole)."""
    _instance(plant, world["l2_c"], "compliant")
    report = run_gap_analysis("NIS2", plant)
    c = _item(report, "NIS2-ART21-1.1")
    tisax_link = next(x for x in c["cross"] if x["external_id"] == "ISA-1.1.1")
    assert tisax_link["relationship"] == "parziale"  # min(parziale, equivalente)
    assert tisax_link["via"] == "A.5.1"
    assert c["state"] == "parziale_riuso"


# ── Stato diretto ed esclusioni ──────────────────────────────────────────────

@pytest.mark.django_db
def test_direct_compliant_is_coperto(plant, world):
    _instance(plant, world["acn_m1"], "compliant")
    report = run_gap_analysis("ACN_NIS2", plant, profile="importante")
    assert _item(report, "ACN-GV.PO-01")["state"] == "coperto"
    assert report["coverage"]["direct_pct"] == 50.0  # 1 req su 2


@pytest.mark.django_db
def test_na_excluded_from_denominator(plant, world):
    _instance(plant, world["acn_m1"], "na")
    report = run_gap_analysis("ACN_NIS2", plant, profile="importante")
    assert _item(report, "ACN-GV.PO-01")["state"] == "escluso"
    assert report["coverage"]["applicable"] == 1  # resta solo m2


@pytest.mark.django_db
def test_soa_exclusion_excluded(plant, world):
    _instance(plant, world["iso_a"], "non_valutato", applicability="escluso")
    report = run_gap_analysis("ISO27001", plant)
    assert _item(report, "A.5.1")["state"] == "escluso"


# ── TISAX profili ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_tisax_al2_excludes_l3(plant, world):
    report = run_gap_analysis("TISAX", plant, profile="AL2")
    ids = {i["external_id"] for i in report["items"]}
    assert ids == {"ISA-1.1.1"}


@pytest.mark.django_db
def test_tisax_al3_includes_l3_and_base_inherits_vh_status(plant, world):
    _instance(plant, world["l3_c"], "compliant")  # solo il VH è valutato
    report = run_gap_analysis("TISAX", plant, profile="AL3")
    ids = {i["external_id"] for i in report["items"]}
    assert ids == {"ISA-1.1.1", "ISA-1.1.1-VH"}
    # il base L2 (superseded in M03) eredita lo stato del suo VH
    assert _item(report, "ISA-1.1.1")["state"] == "coperto"
    assert _item(report, "ISA-1.1.1-VH")["state"] == "coperto"


@pytest.mark.django_db
def test_tisax_vh_na_is_authoritative_over_base(plant, world):
    """Il VH valutato è l'istanza autoritativa (in M03 il base è superseded):
    un VH 'na' deve dare 'escluso' anche se il base è non_valutato o gap —
    nell'ordine di stato 'na' valeva 0 e perdeva il confronto (code review)."""
    _instance(plant, world["l3_c"], "na")
    _instance(plant, world["l2_c"], "non_valutato")
    report = run_gap_analysis("TISAX", plant, profile="AL3")
    assert _item(report, "ISA-1.1.1")["state"] == "escluso"
    assert _item(report, "ISA-1.1.1-VH")["state"] == "escluso"


@pytest.mark.django_db
def test_tisax_vh_inherits_cross_links_of_base(plant, world):
    """Il crosswalk punta agli ID L2: il VH eredita i cross-link del base."""
    _instance(plant, world["iso_a"], "compliant")
    report = run_gap_analysis("TISAX", plant, profile="AL3")
    vh = _item(report, "ISA-1.1.1-VH")
    assert any(c["external_id"] == "A.5.1" for c in vh["cross"])
    assert vh["state"] == "coperto_riuso"

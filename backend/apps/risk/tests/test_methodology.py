"""Metodologia D-ITA-INF-23: matrice, policy di governo, catalogo minacce,
classi di informazioni, cicli di valutazione e archiviazione del registro
precedente."""
import datetime
import json
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from apps.risk import services
from apps.risk.models import (
    InformationClass,
    RiskAssessmentCycle,
    RiskGovernancePolicy,
    ThreatCatalogEntry,
)

User = get_user_model()

CATALOG_FILE = Path(__file__).resolve().parents[3] / "risk_catalogs" / "threats.json"


# ── fixture ──────────────────────────────────────────────────────────────────

def _plant(code, **extra):
    from apps.plants.models import Plant

    values = {"name": f"Plant {code}", "country": "IT", "nis2_scope": "importante", "status": "attivo"}
    values.update(extra)
    return Plant.objects.create(code=code, **values)


@pytest.fixture
def plant(db):
    return _plant("MT-A")


@pytest.fixture
def other_plant(db):
    return _plant("MT-B", country="PL")


@pytest.fixture
def org_user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess

    user = User.objects.create_user(username="org@test.com", email="org@test.com", password="x")
    UserPlantAccess.objects.create(user=user, role=GrcRole.RISK_MANAGER, scope_type="org")
    return user


@pytest.fixture
def site_user(db, plant):
    from apps.auth_grc.models import GrcRole, UserPlantAccess

    user = User.objects.create_user(username="site@test.com", email="site@test.com", password="x")
    access = UserPlantAccess.objects.create(user=user, role=GrcRole.RISK_MANAGER, scope_type="single_plant")
    access.scope_plants.add(plant)
    return user


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


# ── matrice e regole di calcolo ──────────────────────────────────────────────

EXPECTED_MATRIX = {
    5: ["medium", "high", "high", "critical", "critical"],
    4: ["low", "medium", "high", "critical", "critical"],
    3: ["low", "medium", "medium", "high", "critical"],
    2: ["very_low", "low", "medium", "high", "high"],
    1: ["very_low", "low", "low", "medium", "high"],
}


def test_risk_class_matches_procedure_matrix():
    for p, row in EXPECTED_MATRIX.items():
        for i, expected in enumerate(row, start=1):
            assert services.risk_class(p, i) == expected, (p, i)


def test_risk_class_ignores_numeric_product():
    # Celle in cui il vecchio prodotto P×I dava un'altra classe (procedura §8).
    assert services.risk_class(5, 3) == "high"      # 15, era Critical
    assert services.risk_class(2, 4) == "high"      # 8, era Medium
    assert services.risk_class(1, 5) == "high"      # 5, era Medium
    assert services.risk_class(4, 1) == "low"       # 4, era Medium


def test_risk_class_missing_or_out_of_range():
    assert services.risk_class(None, 3) is None
    assert services.risk_class(3, 0) is None
    assert services.risk_class(6, 3) is None


def test_shift_class_respects_bounds_and_floor():
    assert services.shift_class("medium", +1) == "high"
    assert services.shift_class("critical", +1) == "critical"
    assert services.shift_class("very_low", -1) == "very_low"
    assert services.shift_class("high", -1, floor="high") == "high"


def test_overall_impact_is_worst_case_with_confidentiality_floor():
    dims = {"economic": 2, "legal": 3, "operational": None, "unknown": 5}
    assert services.overall_impact(dims) == 3
    floor = services.confidentiality_floor(["normal", "very_high"])
    assert floor == 5
    assert services.overall_impact(dims, floor) == 5
    assert services.overall_impact({}) is None


def test_bucket_and_treatment_rule():
    assert services.risk_level_bucket("low") == "verde"
    assert services.risk_level_bucket("medium") == "giallo"
    assert services.risk_level_bucket("critical") == "rosso"
    assert services.risk_level_bucket(None) is None
    assert services.treatment_rule("critical") == {"rule": "mandatory", "months": 3}
    assert services.treatment_rule("high")["months"] == 12


def test_economic_level():
    th = services.DEFAULT_ECONOMIC_THRESHOLDS
    assert services.economic_level(5_000, th) == 1
    assert services.economic_level(10_000, th) == 2
    assert services.economic_level(300_000, th) == 4
    assert services.economic_level(2_000_000, th) == 5


# ── policy di governo ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_default_preset_depends_on_number_of_sites(plant):
    assert services.resolve_policy(plant)["preset"] == "sito_singolo"
    _plant("MT-C")
    policy = services.resolve_policy(plant)
    assert policy["preset"] == "centralizzato"
    assert policy["configured"] is False
    assert policy["upper_opinion"]["high"] == "binding"


@pytest.mark.django_db
def test_plant_override_merges_key_by_key(plant, other_plant):
    RiskGovernancePolicy.objects.create(plant=None, preset="federato")
    RiskGovernancePolicy.objects.create(
        plant=plant, economic_thresholds={"2": 5000, "3": 20000, "4": 100000, "5": 200000},
        upper_opinion={"high": "binding"},
    )
    site = services.resolve_policy(plant)
    assert site["preset"] == "federato"
    assert site["upper_opinion"]["high"] == "binding"
    assert site["upper_opinion"]["critical"] == "binding"
    assert site["economic_thresholds"]["5"] == 200000
    other = services.resolve_policy(other_plant)
    assert other["upper_opinion"]["high"] == "notify"
    assert other["economic_thresholds"] == services.DEFAULT_ECONOMIC_THRESHOLDS


@pytest.mark.django_db
def test_save_policy_requires_org_scope(site_user, plant):
    with pytest.raises(PermissionDenied):
        services.save_governance_policy(site_user, plant, {"overdue_escalation_days": 10})


@pytest.mark.django_db
def test_save_policy_validation(org_user, plant):
    with pytest.raises(ValidationError):
        services.save_governance_policy(org_user, None, {"economic_thresholds": {"2": 9, "3": 5, "4": 7, "5": 8}})
    with pytest.raises(ValidationError):
        services.save_governance_policy(org_user, None, {"upper_opinion": {"high": "maybe"}})
    with pytest.raises(ValidationError):
        services.save_governance_policy(org_user, plant, {"preset": "federato"})


@pytest.mark.django_db
def test_save_policy_upserts_and_audits(org_user):
    from core.audit import AuditLog

    services.save_governance_policy(org_user, None, {"preset": "centralizzato", "overdue_escalation_days": 20})
    services.save_governance_policy(org_user, None, {"overdue_escalation_days": 15})
    assert RiskGovernancePolicy.objects.filter(plant__isnull=True).count() == 1
    assert services.resolve_policy(None)["overdue_escalation_days"] == 15
    assert AuditLog.objects.filter(action_code="risk.policy.updated").count() == 2


@pytest.mark.django_db
def test_policy_api_resolved_and_save(org_user, plant):
    c = _client(org_user)
    res = c.post("/api/v1/risk/governance-policies/save/",
                 {"plant": None, "preset": "centralizzato"}, format="json")
    assert res.status_code == 200, res.content
    res = c.get(f"/api/v1/risk/governance-policies/resolved/?plant={plant.pk}")
    assert res.status_code == 200
    assert res.json()["preset"] == "centralizzato"
    res = c.get("/api/v1/risk/governance-policies/presets/")
    assert set(res.json()) == {"centralizzato", "federato", "sito_singolo"}


# ── catalogo minacce ─────────────────────────────────────────────────────────

def test_catalog_file_is_complete():
    data = json.loads(CATALOG_FILE.read_text("utf-8"))
    codes = [t["code"] for t in data["threats"]]
    assert len(codes) == len(set(codes))
    for t in data["threats"]:
        assert set(t["asset_types"]) <= set(data["asset_types"]), t["code"]
        assert set(t["translations"]) == {"it", "en", "fr", "pl", "tr"}, t["code"]
        assert all(v.get("title") for v in t["translations"].values()), t["code"]
    # Voci richieste dalla procedura §6.3 oltre al catalogo aziendale
    for code in ("IN_MAL", "IN_PHI", "IN_DOS", "IN_VUL", "PR_FUR", "IN_MOD", "LO_TER"):
        assert code in codes
    assert {t for th in data["threats"] for t in th["asset_types"]} == set(data["asset_types"])


@pytest.mark.django_db
def test_load_risk_catalog_is_idempotent():
    call_command("load_risk_catalog")
    total = ThreatCatalogEntry.objects.count()
    call_command("load_risk_catalog")
    assert ThreatCatalogEntry.objects.count() == total
    assert ThreatCatalogEntry.objects.get(code="IN_MOD").get_title("en").startswith("Unauthorised")


@pytest.mark.django_db
def test_sync_deactivates_removed_and_keeps_custom():
    ThreatCatalogEntry.objects.create(code="X_CUSTOM", asset_types=["IT"], source="custom",
                                      translations={"it": {"title": "Mia"}})
    base = {"version": "1", "threats": [
        {"code": "A_ONE", "asset_types": ["IT"], "cia": ["C"], "translations": {"it": {"title": "Uno"}}},
        {"code": "A_TWO", "asset_types": ["SEDE"], "cia": ["A"], "translations": {"it": {"title": "Due"}}},
    ]}
    services.sync_threat_catalog(base)
    counts = services.sync_threat_catalog({"version": "2", "threats": [
        base["threats"][0],
        {"code": "X_CUSTOM", "asset_types": ["IT"], "cia": [], "translations": {"it": {"title": "Altro"}}},
    ]})
    assert counts["deactivated"] == 1
    assert counts["conflicts"] == ["X_CUSTOM"]
    assert ThreatCatalogEntry.objects.get(code="A_TWO").active is False
    custom = ThreatCatalogEntry.objects.get(code="X_CUSTOM")
    assert custom.source == "custom" and custom.get_title() == "Mia"


@pytest.mark.django_db
def test_custom_threat_api(org_user, site_user):
    c = _client(org_user)
    payload = {"code": "cu_test", "asset_types": ["SEDE"], "cia": ["A"],
               "translations": {"it": {"title": "Allagamento del magazzino"}}}
    res = c.post("/api/v1/risk/threats/", payload, format="json")
    assert res.status_code == 201, res.content
    entry_id = res.json()["id"]
    assert res.json()["code"] == "CU_TEST" and res.json()["source"] == "custom"
    assert c.post("/api/v1/risk/threats/", payload, format="json").status_code == 400
    res = c.patch(f"/api/v1/risk/threats/{entry_id}/", {"cia": ["A", "I"]}, format="json")
    assert res.status_code == 200 and res.json()["cia"] == ["A", "I"]
    assert c.delete(f"/api/v1/risk/threats/{entry_id}/").status_code == 204
    assert ThreatCatalogEntry.objects.get(pk=entry_id).active is False
    # chi ha un solo sito non gestisce il catalogo
    assert _client(site_user).post("/api/v1/risk/threats/", {**payload, "code": "CU_TWO"},
                                   format="json").status_code == 403


@pytest.mark.django_db
def test_catalog_entries_are_read_only(org_user):
    entry = ThreatCatalogEntry.objects.create(code="CAT_X", asset_types=["IT"], source="catalog",
                                              translations={"it": {"title": "Cat"}})
    c = _client(org_user)
    assert c.patch(f"/api/v1/risk/threats/{entry.pk}/", {"cia": ["C"]}, format="json").status_code == 400
    assert c.delete(f"/api/v1/risk/threats/{entry.pk}/").status_code == 400


@pytest.mark.django_db
def test_threat_list_filters(org_user):
    ThreatCatalogEntry.objects.create(code="F_IT", asset_types=["IT"], source="catalog",
                                      translations={"it": {"title": "Furto informazioni"}})
    ThreatCatalogEntry.objects.create(code="F_SEDE", asset_types=["SEDE"], source="catalog",
                                      translations={"it": {"title": "Terremoto"}})
    c = _client(org_user)
    codes = [t["code"] for t in c.get("/api/v1/risk/threats/?asset_type=SEDE").json()["results"]]
    assert codes == ["F_SEDE"]
    codes = [t["code"] for t in c.get("/api/v1/risk/threats/?q=furto").json()["results"]]
    assert codes == ["F_IT"]


# ── classi di informazioni ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_information_class_scope(site_user, plant, other_plant):
    from apps.bia.models import CriticalProcess

    c = _client(site_user)
    res = c.post("/api/v1/risk/information-classes/",
                 {"plant": str(plant.pk), "name": "Disegni OEM", "confidentiality": "high"}, format="json")
    assert res.status_code == 201, res.content
    # classe di gruppo: solo scope organizzazione
    res = c.post("/api/v1/risk/information-classes/", {"plant": None, "name": "ERP"}, format="json")
    assert res.status_code == 403
    process = CriticalProcess.objects.create(plant=other_plant, name="Altro sito")
    res = c.post("/api/v1/risk/information-classes/",
                 {"plant": str(plant.pk), "name": "X", "critical_processes": [str(process.pk)]}, format="json")
    assert res.status_code == 400
    assert InformationClass.objects.filter(plant=plant).count() == 1


# ── cicli di valutazione ─────────────────────────────────────────────────────

@pytest.mark.django_db
def test_start_first_cycle_rules(org_user, plant):
    cycle = services.start_cycle(org_user, plant, "primo")
    assert cycle.status == "in_corso"
    with pytest.raises(ValidationError):
        services.start_cycle(org_user, plant, "primo")
    cycle.status = "approvato"
    cycle.approved_at = cycle.started_at
    cycle.save()
    with pytest.raises(ValidationError):
        services.start_cycle(org_user, plant, "primo")
    with pytest.raises(ValidationError):
        services.start_cycle(org_user, plant, "straordinario", "")
    revision = services.start_cycle(org_user, plant, "straordinario", "Incidente significativo")
    assert services.open_cycle(plant) == revision
    assert services.approved_cycle(plant) == cycle


@pytest.mark.django_db
def test_revision_needs_approved_cycle_and_legacy_does_not_count(org_user, plant):
    RiskAssessmentCycle.objects.create(plant=plant, kind="legacy", status="archiviato",
                                       started_at=datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc))
    with pytest.raises(ValidationError):
        services.start_cycle(org_user, plant, "periodico")
    assert services.start_cycle(org_user, plant, "primo").kind == "primo"


@pytest.mark.django_db
def test_group_cycle_requires_org_scope_and_enabled_register(org_user, site_user, plant):
    with pytest.raises(PermissionDenied):
        services.start_cycle(site_user, None, "primo")
    # un solo sito → preset sito singolo → nessun registro di gruppo
    with pytest.raises(ValidationError):
        services.start_cycle(org_user, None, "primo")
    _plant("MT-D")
    assert services.start_cycle(org_user, None, "primo").plant is None


@pytest.mark.django_db
def test_cycle_api(site_user, plant, other_plant):
    c = _client(site_user)
    res = c.post("/api/v1/risk/cycles/start/", {"plant": str(plant.pk), "kind": "primo"}, format="json")
    assert res.status_code == 201, res.content
    res = c.post("/api/v1/risk/cycles/start/", {"plant": str(other_plant.pk), "kind": "primo"}, format="json")
    assert res.status_code == 403
    listed = c.get("/api/v1/risk/cycles/").json()["results"]
    assert [x["plant"] for x in listed] == [str(plant.pk)]
    assert listed[0]["risks_count"] == 0


# ── perimetro ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_asset_types_present(plant):
    from apps.controls.models import Framework
    from apps.plants.models import PlantFramework
    from apps.suppliers.models import Supplier

    assert services.asset_types_present(plant) == ["IT", "SEDE", "PERSONALE"]
    plant.has_ot = True
    plant.save()
    Supplier.objects.create(name="Fornitore").plants.add(plant)
    fw = Framework.objects.create(code="TISAX_PROTO", name="Proto", version="6", published_at=datetime.date(2024, 1, 1))
    PlantFramework.objects.create(plant=plant, framework=fw, active_from=datetime.date(2024, 1, 1))
    assert services.plant_handles_prototypes(plant) is True
    assert services.asset_types_present(plant) == ["IT", "OT", "SEDE", "PERSONALE", "FORNITORI", "PROTOTIPI"]
    assert services.asset_types_present(None) == ["IT", "PERSONALE", "FORNITORI"]


@pytest.mark.django_db
def test_asset_types_suppliers_org_wide(plant):
    """Un fornitore attivo senza sito vale per tutta l'organizzazione."""
    from apps.suppliers.models import Supplier

    other = _plant("ALTRO-1")
    Supplier.objects.create(name="Di un altro sito").plants.add(other)
    assert "FORNITORI" not in services.asset_types_present(plant)
    Supplier.objects.create(name="Terminato", status="terminato")
    assert "FORNITORI" not in services.asset_types_present(plant)
    Supplier.objects.create(name="Di organizzazione")
    assert "FORNITORI" in services.asset_types_present(plant)


@pytest.mark.django_db
def test_plant_is_eu():
    assert _plant("EU-1", country="PL").is_eu is True
    assert _plant("TN-1", country="TN", nis2_scope="non_soggetto").is_eu is False

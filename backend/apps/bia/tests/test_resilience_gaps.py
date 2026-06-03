"""P2-4 — catena BIA→BCP→Risk.

Verifica `get_resilience_gap_register`: i processi critici con RTO target ma
senza copertura BCP adeguata (nessun piano approvato o piano insufficiente)
diventano voci di un registro rischi di resilienza, esposto via API plant-scoped.
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.bcp.models import BcpPlan
from apps.bia.models import CriticalProcess
from apps.bia.services import get_resilience_gap_register
from apps.plants.models import Plant

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def plant(db):
    return Plant.objects.create(
        code="RG-P", name="Plant RG", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


def _proc(plant, name, rto_target, criticality=3):
    return CriticalProcess.objects.create(
        plant=plant, name=name, criticality=criticality,
        rto_target_hours=rto_target,
    )


def _approved_plan(plant, proc, rto_hours, status="approvato"):
    plan = BcpPlan.objects.create(
        plant=plant, title=f"BCP {proc.name}", status=status, rto_hours=rto_hours,
    )
    plan.critical_processes.add(proc)
    return plan


# ── service ─────────────────────────────────────────────────────────────────


def test_no_bcp_plan_is_high(plant):
    _proc(plant, "P-noplan", rto_target=10)
    reg = get_resilience_gap_register()
    assert reg["count"] == 1
    item = reg["items"][0]
    assert item["gap"] == "no_bcp_plan"
    assert item["bcp_status"] == "unknown"
    assert item["risk_level"] == "alto"


def test_adequate_bcp_excluded(plant):
    proc = _proc(plant, "P-ok", rto_target=10)
    _approved_plan(plant, proc, rto_hours=8)   # ratio 0.8 → ok
    assert get_resilience_gap_register()["count"] == 0


def test_marginal_bcp_is_medio(plant):
    proc = _proc(plant, "P-marg", rto_target=10)
    _approved_plan(plant, proc, rto_hours=12)  # ratio 1.2 → warning
    reg = get_resilience_gap_register()
    assert reg["items"][0]["gap"] == "bcp_marginal"
    assert reg["items"][0]["risk_level"] == "medio"


def test_insufficient_bcp_is_alto(plant):
    proc = _proc(plant, "P-insuf", rto_target=10)
    _approved_plan(plant, proc, rto_hours=20)  # ratio 2.0 → critical
    reg = get_resilience_gap_register()
    assert reg["items"][0]["gap"] == "bcp_insufficient"
    assert reg["items"][0]["risk_level"] == "alto"


def test_high_criticality_bumps_level(plant):
    _proc(plant, "P-crit", rto_target=10, criticality=5)  # no plan: alto → bump → critico
    reg = get_resilience_gap_register()
    assert reg["items"][0]["risk_level"] == "critico"


def test_marginal_high_criticality_bumps_to_alto(plant):
    proc = _proc(plant, "P-marg5", rto_target=10, criticality=4)
    _approved_plan(plant, proc, rto_hours=12)  # warning → medio → bump → alto
    assert get_resilience_gap_register()["items"][0]["risk_level"] == "alto"


def test_without_rto_target_excluded(plant):
    CriticalProcess.objects.create(plant=plant, name="P-nodato", criticality=5)
    assert get_resilience_gap_register()["count"] == 0


def test_only_approved_plans_count(plant):
    proc = _proc(plant, "P-bozza", rto_target=10)
    _approved_plan(plant, proc, rto_hours=8, status="bozza")  # piano in bozza → ignorato
    reg = get_resilience_gap_register()
    assert reg["count"] == 1
    assert reg["items"][0]["gap"] == "no_bcp_plan"


def test_counts_and_attention(plant):
    _proc(plant, "P1", rto_target=10)                       # no plan → alto
    p2 = _proc(plant, "P2", rto_target=10)
    _approved_plan(plant, p2, rto_hours=12)                 # marginal → medio
    _proc(plant, "P3", rto_target=10, criticality=5)        # no plan + crit → critico
    reg = get_resilience_gap_register()
    assert reg["by_level"] == {"medio": 1, "alto": 1, "critico": 1}
    assert reg["attention"] == 2   # alto + critico


def test_sorted_by_severity(plant):
    p1 = _proc(plant, "Marginale", rto_target=10)
    _approved_plan(plant, p1, rto_hours=12)                 # medio
    _proc(plant, "Critico", rto_target=10, criticality=5)   # critico
    _proc(plant, "Alto", rto_target=10)                     # alto
    levels = [i["risk_level"] for i in get_resilience_gap_register()["items"]]
    assert levels == ["critico", "alto", "medio"]


def test_item_includes_plant_name(plant):
    _proc(plant, "P-plant", rto_target=10)
    assert get_resilience_gap_register()["items"][0]["plant"] == "Plant RG"


# ── API ─────────────────────────────────────────────────────────────────────


def test_api_resilience_gaps_org_scope(plant):
    u = User.objects.create_user(username="rg", email="rg@t.com", password="x")
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    _proc(plant, "Scoperto", rto_target=10)

    client = APIClient()
    client.force_authenticate(user=u)
    resp = client.get(reverse("critical-process-resilience-gaps"))
    assert resp.status_code == 200
    assert resp.data["count"] == 1
    assert resp.data["items"][0]["process_name"] == "Scoperto"


def test_api_resilience_gaps_plant_scoped(plant):
    from apps.auth_grc.models import GrcRole, UserPlantAccess

    other = Plant.objects.create(code="RG-O", name="Altro", country="IT", nis2_scope="non_soggetto", status="attivo")
    _proc(other, "Solo altro plant", rto_target=10)

    u = User.objects.create_user(username="rg2", email="rg2@t.com", password="x")
    access = UserPlantAccess.objects.create(user=u, role=GrcRole.RISK_MANAGER, scope_type="plant")
    access.scope_plants.set([plant])

    client = APIClient()
    client.force_authenticate(user=u)
    resp = client.get(reverse("critical-process-resilience-gaps"))
    assert resp.status_code == 200
    names = [i["process_name"] for i in resp.data["items"]]
    assert "Solo altro plant" not in names

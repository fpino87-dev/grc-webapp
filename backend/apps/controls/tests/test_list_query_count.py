"""
Test C2 — la lista istanze controllo deve avere un numero di query PIATTO.

Prima del fix, suggested_status/suggestion_differs/calc_maturity_level
rieseguivano check su documenti/evidenze con `.exists()`/`.count()` per OGNI
riga (più volte): il numero di query cresceva linearmente con le istanze.
Ora i filtri girano in Python sulla cache del prefetch: il conteggio query
con 12 istanze deve essere identico a quello con 3.
"""
import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_INSTANCES = "/api/v1/controls/instances/"


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="qc_user", email="qc@test.com", password="test")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def env(db, user):
    """Plant + framework attivo; factory per istanze con requisiti ed evidenze."""
    from apps.controls.models import Control, ControlInstance, Framework
    from apps.documents.models import Evidence
    from apps.plants.models import Plant, PlantFramework

    plant = Plant.objects.create(
        code="QC-P", name="Plant QueryCount", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )
    fw = Framework.objects.create(
        code="ISO-QC", name="ISO QC", version="2022",
        published_at=timezone.localdate(),
    )
    PlantFramework.objects.create(
        plant=plant, framework=fw,
        active_from=timezone.localdate(), level="L2", active=True,
    )

    counter = {"n": 0}

    def make_instance(status="parziale"):
        counter["n"] += 1
        n = counter["n"]
        control = Control.objects.create(
            framework=fw, external_id=f"QC-{n}",
            translations={"it": {"title": f"Controllo {n}"}},
            evidence_requirement={
                "min_evidences": 1,
                "evidences": [
                    {"type": "report", "mandatory": True, "description": "Report"},
                ],
            },
        )
        inst = ControlInstance.objects.create(
            plant=plant, control=control, status=status, created_by=user,
        )
        ev = Evidence.objects.create(
            title=f"Evidenza {n}", evidence_type="report",
            valid_until=timezone.localdate(), plant=plant, created_by=user,
        )
        inst.evidences.add(ev)
        return inst

    return make_instance


def _count_queries(client) -> int:
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    with CaptureQueriesContext(connection) as ctx:
        resp = client.get(URL_INSTANCES)
        assert resp.status_code == 200
    return len(ctx)


@pytest.mark.django_db
def test_instances_list_query_count_is_flat(client, env):
    for _ in range(3):
        env()
    q_small = _count_queries(client)

    for _ in range(9):
        env()
    q_large = _count_queries(client)

    assert q_large == q_small, (
        f"Il numero di query cresce con le righe: {q_small} con 3 istanze, "
        f"{q_large} con 12 — suggested_status/maturity non stanno usando il prefetch"
    )


@pytest.mark.django_db
def test_detail_info_query_count_is_bounded(client, env):
    """Il drawer non deve rieseguire check_evidence_requirements più volte."""
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    inst = env()
    with CaptureQueriesContext(connection) as ctx:
        resp = client.get(f"{URL_INSTANCES}{inst.id}/detail-info/")
        assert resp.status_code == 200
    # bound largo ma sufficiente a beccare la regressione (prima: ~4 passate
    # complete di check_evidence_requirements + query per maturity)
    assert len(ctx) <= 25, f"detail-info esegue {len(ctx)} query"

    data = resp.json()
    assert data["suggested_status"] == "compliant"
    assert "requirements" in data

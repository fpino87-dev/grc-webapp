"""Test API cicli PDCA."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_CYCLES = "/api/v1/pdca/cycles/"


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="pdca_user", email="pdca@test.com", password="test")
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
    return Plant.objects.create(code="PDCA-P", name="Plant PDCA", country="IT", nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def cycle(db, plant, user):
    from apps.pdca.services import create_cycle
    return create_cycle(plant=plant, title="Ciclo Test", trigger_type="controllo")


# ── CRUD ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_cycles_authenticated(client):
    resp = client.get(URL_CYCLES)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_list_cycles_unauthenticated():
    resp = APIClient().get(URL_CYCLES)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_create_cycle(client, plant):
    payload = {
        "plant": str(plant.id),
        "title": "Ciclo API Test",
        "trigger_type": "controllo",
        "scope_type": "custom",
    }
    resp = client.post(URL_CYCLES, payload, format="json")
    assert resp.status_code == 201
    assert resp.data["title"] == "Ciclo API Test"
    assert resp.data["fase_corrente"] == "plan"


@pytest.mark.django_db
def test_retrieve_cycle(client, cycle):
    resp = client.get(f"{URL_CYCLES}{cycle.id}/")
    assert resp.status_code == 200
    assert resp.data["title"] == "Ciclo Test"


@pytest.mark.django_db
def test_delete_cycle_requires_reason(client, cycle):
    """Cancellazione senza motivo (o motivo troppo corto) -> 400."""
    resp = client.delete(f"{URL_CYCLES}{cycle.id}/")
    assert resp.status_code == 400

    resp_short = client.delete(
        f"{URL_CYCLES}{cycle.id}/",
        data={"reason": "x"},
        format="json",
    )
    assert resp_short.status_code == 400


@pytest.mark.django_db
def test_delete_cycle_soft_deletes_cycle_and_phases(client, cycle):
    """Soft delete OK: ciclo e fasi marcate deleted_at, GET ritorna 404."""
    from apps.pdca.models import PdcaCycle, PdcaPhase

    assert cycle.phases.count() == 4
    resp = client.delete(
        f"{URL_CYCLES}{cycle.id}/",
        data={"reason": "creato per errore — annullamento"},
        format="json",
    )
    assert resp.status_code == 204

    # Default manager filtra deleted_at -> 404 in GET
    resp2 = client.get(f"{URL_CYCLES}{cycle.id}/")
    assert resp2.status_code == 404

    # Recuperabile via all_with_deleted con flag valorizzato
    raw = PdcaCycle.objects.all_with_deleted().get(pk=cycle.pk)
    assert raw.deleted_at is not None

    # Cascade: tutte le fasi sono soft-deleted
    phases_remaining = PdcaPhase.objects.filter(cycle=cycle).count()
    assert phases_remaining == 0
    phases_all = PdcaPhase.objects.all_with_deleted().filter(cycle=cycle)
    assert phases_all.count() == 4
    assert all(p.deleted_at is not None for p in phases_all)


@pytest.mark.django_db
def test_delete_cycle_blocked_when_closed(client, cycle, user):
    """Ciclo gia' chiuso -> 400, lesson learned dipende dal cycle.pk."""
    cycle.fase_corrente = "chiuso"
    cycle.save(update_fields=["fase_corrente"])
    resp = client.delete(
        f"{URL_CYCLES}{cycle.id}/",
        data={"reason": "non importa, dovrebbe rifiutare"},
        format="json",
    )
    assert resp.status_code == 400
    assert "chiuso" in resp.json()["error"].lower()


@pytest.mark.django_db
def test_delete_cycle_blocked_with_open_finding(client, cycle, plant, user):
    """Finding aperto collegato -> 400."""
    from apps.audit_prep.models import AuditFinding, AuditPrep
    from datetime import date

    prep = AuditPrep.objects.create(
        plant=plant, title="Audit",
        audit_date=date.today(), status="in_corso", created_by=user,
    )
    AuditFinding.objects.create(
        audit_prep=prep, pdca_cycle=cycle,
        finding_type="major_nc", title="open finding",
        description="d", audit_date=date.today(),
        status="open", created_by=user,
    )
    resp = client.delete(
        f"{URL_CYCLES}{cycle.id}/",
        data={"reason": "non importa, dovrebbe rifiutare"},
        format="json",
    )
    assert resp.status_code == 400
    assert "finding" in resp.json()["error"].lower()


@pytest.mark.django_db
def test_delete_cycle_cascades_auto_generated_open_finding(client, cycle, plant, user):
    """Finding aperti `auto_generated=True` non bloccano: vengono soft-deleted
    insieme al ciclo (sono parte della stessa catena di auto-validazione)."""
    from apps.audit_prep.models import AuditFinding, AuditPrep
    from datetime import date

    prep = AuditPrep.objects.create(
        plant=plant, title="Audit",
        audit_date=date.today(), status="in_corso", created_by=user,
    )
    auto_finding = AuditFinding.objects.create(
        audit_prep=prep, pdca_cycle=cycle,
        finding_type="minor_nc", title="auto-generated finding",
        description="d", audit_date=date.today(),
        status="open", auto_generated=True, created_by=user,
    )
    resp = client.delete(
        f"{URL_CYCLES}{cycle.id}/",
        data={"reason": "ciclo auto-generato non piu' necessario"},
        format="json",
    )
    assert resp.status_code == 204

    auto_finding.refresh_from_db()
    assert auto_finding.deleted_at is not None


@pytest.mark.django_db
def test_delete_cycle_blocked_with_manual_open_finding_even_with_auto(
    client, cycle, plant, user,
):
    """Mix: 1 manuale + 1 auto-generato aperti -> blocco a causa del manuale.
    Il messaggio di errore deve specificare 'manuali'."""
    from apps.audit_prep.models import AuditFinding, AuditPrep
    from datetime import date

    prep = AuditPrep.objects.create(
        plant=plant, title="Audit",
        audit_date=date.today(), status="in_corso", created_by=user,
    )
    AuditFinding.objects.create(
        audit_prep=prep, pdca_cycle=cycle,
        finding_type="major_nc", title="manual finding",
        description="d", audit_date=date.today(),
        status="open", auto_generated=False, created_by=user,
    )
    AuditFinding.objects.create(
        audit_prep=prep, pdca_cycle=cycle,
        finding_type="minor_nc", title="auto finding",
        description="d", audit_date=date.today(),
        status="open", auto_generated=True, created_by=user,
    )
    resp = client.delete(
        f"{URL_CYCLES}{cycle.id}/",
        data={"reason": "ciclo non piu' utile"},
        format="json",
    )
    assert resp.status_code == 400
    assert "manuali" in resp.json()["error"].lower()


@pytest.mark.django_db
def test_delete_cycle_allowed_with_only_closed_findings(client, cycle, plant, user):
    """Finding gia' chiusi non bloccano la cancellazione."""
    from apps.audit_prep.models import AuditFinding, AuditPrep
    from datetime import date

    prep = AuditPrep.objects.create(
        plant=plant, title="Audit",
        audit_date=date.today(), status="in_corso", created_by=user,
    )
    AuditFinding.objects.create(
        audit_prep=prep, pdca_cycle=cycle,
        finding_type="minor_nc", title="closed finding",
        description="d", audit_date=date.today(),
        status="closed", created_by=user,
    )
    resp = client.delete(
        f"{URL_CYCLES}{cycle.id}/",
        data={"reason": "ciclo doppio per errore"},
        format="json",
    )
    assert resp.status_code == 204


# ── advance action ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_advance_cycle_from_plan_to_do(client, cycle, user):
    assert cycle.fase_corrente == "plan"
    resp = client.post(
        f"{URL_CYCLES}{cycle.id}/advance/",
        {"notes": "Piano completato con tutti i requisiti necessari"},  # >= 20 chars
        format="json",
    )
    assert resp.status_code == 200
    cycle.refresh_from_db()
    assert cycle.fase_corrente == "do"


@pytest.mark.django_db
def test_advance_closed_cycle_returns_error(client, cycle, user):
    cycle.fase_corrente = "chiuso"
    cycle.save()
    resp = client.post(f"{URL_CYCLES}{cycle.id}/advance/", {}, format="json")
    assert resp.status_code in (400, 422)


# ── create_cycle service ──────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_cycle_incident_starts_at_act(plant, user):
    from apps.pdca.services import create_cycle
    cycle = create_cycle(plant=plant, title="Incidente Cycle", trigger_type="incidente")
    assert cycle.fase_corrente == "act"


@pytest.mark.django_db
def test_create_cycle_creates_all_phases(plant, user):
    from apps.pdca.services import create_cycle
    from apps.pdca.models import PdcaPhase
    cycle = create_cycle(plant=plant, title="Full Phases", trigger_type="rischio")
    phases = PdcaPhase.objects.filter(cycle=cycle).values_list("phase", flat=True)
    assert set(phases) == {"plan", "do", "check", "act"}


# ── RBAC plant scoping (S1) ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_pm_does_not_see_pdca_cycles_of_other_plant(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    from apps.pdca.models import PdcaCycle
    from apps.plants.models import Plant

    plant_a = Plant.objects.create(
        code="PD-A", name="A", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )
    plant_b = Plant.objects.create(
        code="PD-B", name="B", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )
    PdcaCycle.objects.create(plant=plant_a, title="Cycle A", trigger_type="rischio")
    PdcaCycle.objects.create(plant=plant_b, title="Cycle B", trigger_type="rischio")

    pm = User.objects.create_user(username="pm_pdca", email="pmpdca@test", password="x")
    access = UserPlantAccess.objects.create(
        user=pm, role=GrcRole.PLANT_MANAGER, scope_type="single_plant",
    )
    access.scope_plants.set([plant_a])

    c = APIClient()
    c.force_authenticate(user=pm)
    resp = c.get(URL_CYCLES)
    assert resp.status_code == 200
    titles = {item["title"] for item in resp.data["results"]}
    assert titles == {"Cycle A"}

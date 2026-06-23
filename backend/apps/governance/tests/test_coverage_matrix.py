"""Test matrice di copertura ruoli (RoleRequirement + get_role_coverage_matrix)."""
import pytest
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

User = get_user_model()

URL_MATRIX = "/api/v1/governance/role-assignments/coverage-matrix/"
URL_REQUIREMENTS = "/api/v1/governance/role-requirements/"


@pytest.fixture
def org_user(db):
    """Utente con scope org (vede tutti i siti) e permesso di scrittura governance."""
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="cov_user", email="cov@test.com", password="test")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def client(org_user):
    c = APIClient()
    c.force_authenticate(user=org_user)
    return c


@pytest.fixture
def nis2_plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="N2", name="Plant NIS2", country="IT", nis2_scope="essenziale", status="attivo")


@pytest.fixture
def plain_plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="P1", name="Plant base", country="IT", nis2_scope="non_soggetto", status="attivo")


def _assign(user, role, scope_type, scope_id=None, valid_until=None):
    from apps.governance.models import RoleAssignment
    return RoleAssignment.objects.create(
        user=user, role=role, scope_type=scope_type, scope_id=scope_id,
        valid_from=timezone.localdate(), valid_until=valid_until,
    )


def _org_status(matrix, role):
    return next(r["status"] for r in matrix["org_roles"] if r["role"] == role)


def _plant_row(matrix, role):
    return next(r for r in matrix["plant_roles"] if r["role"] == role)


# ── Seed di default presente ──────────────────────────────────────────────

@pytest.mark.django_db
def test_default_requirements_seeded():
    from apps.governance.models import RoleRequirement
    roles = set(RoleRequirement.objects.values_list("role", flat=True))
    assert {"ciso", "isms_manager", "risk_manager", "internal_auditor", "nis2_contact", "dpo"} <= roles


# ── Ruoli org-level ───────────────────────────────────────────────────────

@pytest.mark.django_db
def test_org_role_vacant_then_covered(org_user):
    from apps.governance.services import get_role_coverage_matrix
    from apps.governance.models import NormativeRole

    m = get_role_coverage_matrix(org_user)
    assert _org_status(m, "ciso") == "vacant"

    _assign(org_user, NormativeRole.CISO, "org")
    m = get_role_coverage_matrix(org_user)
    assert _org_status(m, "ciso") == "covered"


@pytest.mark.django_db
def test_org_role_expiring(org_user):
    from apps.governance.services import get_role_coverage_matrix
    from apps.governance.models import NormativeRole

    _assign(org_user, NormativeRole.RISK_MANAGER, "org",
            valid_until=timezone.localdate() + timedelta(days=10))
    m = get_role_coverage_matrix(org_user)
    assert _org_status(m, "risk_manager") == "expiring"


# ── Ruolo per-sito SENZA fallback (nis2_contact) ──────────────────────────

@pytest.mark.django_db
def test_nis2_contact_per_site_no_org_fallback(org_user, nis2_plant):
    from apps.governance.services import get_role_coverage_matrix
    from apps.governance.models import NormativeRole

    # Un'assegnazione org NON deve coprire il sito (no fallback per nis2_contact)
    _assign(org_user, NormativeRole.NIS2_CONTACT, "org")
    m = get_role_coverage_matrix(org_user)
    cell = _plant_row(m, "nis2_contact")["cells"][str(nis2_plant.id)]
    assert cell["status"] == "vacant"

    # Nomina specifica del sito → coperto
    _assign(org_user, NormativeRole.NIS2_CONTACT, "plant", scope_id=nis2_plant.id)
    m = get_role_coverage_matrix(org_user)
    cell = _plant_row(m, "nis2_contact")["cells"][str(nis2_plant.id)]
    assert cell["status"] == "covered"


@pytest.mark.django_db
def test_nis2_contact_not_applicable_on_non_nis2_plant(org_user, plain_plant):
    from apps.governance.services import get_role_coverage_matrix

    m = get_role_coverage_matrix(org_user)
    cell = _plant_row(m, "nis2_contact")["cells"][str(plain_plant.id)]
    assert cell["status"] == "na"


# ── Ruolo per-sito CON fallback org (dpo) ─────────────────────────────────

@pytest.mark.django_db
def test_dpo_org_fallback_then_site_override(org_user, plain_plant):
    from apps.governance.services import get_role_coverage_matrix
    from apps.governance.models import NormativeRole

    # Senza nulla → vacante
    m = get_role_coverage_matrix(org_user)
    assert _plant_row(m, "dpo")["cells"][str(plain_plant.id)]["status"] == "vacant"

    # DPO org → copre il sito via fallback
    _assign(org_user, NormativeRole.DPO, "org")
    m = get_role_coverage_matrix(org_user)
    cell = _plant_row(m, "dpo")["cells"][str(plain_plant.id)]
    assert cell["status"] == "covered_via_org"
    assert cell.get("via_org") is True

    # Nomina specifica del sito → ha la precedenza
    other = User.objects.create_user(username="dpo_site", email="dpos@test.com", password="t")
    _assign(other, NormativeRole.DPO, "plant", scope_id=plain_plant.id)
    m = get_role_coverage_matrix(org_user)
    cell = _plant_row(m, "dpo")["cells"][str(plain_plant.id)]
    assert cell["status"] == "covered"
    assert not cell.get("via_org")


# ── get_vacant_mandatory_roles deriva dai requirement ─────────────────────

@pytest.mark.django_db
def test_vacant_mandatory_roles_from_requirements(org_user):
    from apps.governance.services import get_vacant_mandatory_roles
    from apps.governance.models import NormativeRole

    vacant = get_vacant_mandatory_roles(None)
    assert "ciso" in vacant and "risk_manager" in vacant

    _assign(org_user, NormativeRole.CISO, "org")
    assert "ciso" not in get_vacant_mandatory_roles(None)


@pytest.mark.django_db
def test_vacant_mandatory_roles_per_plant_respects_applies_to(org_user, plain_plant, nis2_plant):
    from apps.governance.services import get_vacant_mandatory_roles

    # nis2_contact non applicabile a un sito non-NIS2 → non risulta vacante lì
    assert "nis2_contact" not in get_vacant_mandatory_roles(plain_plant)
    # ma è vacante su un sito NIS2 senza nomina
    assert "nis2_contact" in get_vacant_mandatory_roles(nis2_plant)


# ── Endpoint API ──────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_coverage_matrix_endpoint(client, nis2_plant):
    resp = client.get(URL_MATRIX)
    assert resp.status_code == 200
    body = resp.json()
    assert "org_roles" in body and "plant_roles" in body and "plants" in body
    assert any(p["id"] == str(nis2_plant.id) for p in body["plants"])


@pytest.mark.django_db
def test_single_holder_role_blocks_duplicate(client, org_user, nis2_plant):
    """Bug: il Contatto NIS2 (titolare unico) non deve essere assegnabile due volte."""
    payload = {
        "user": org_user.id,
        "role": "nis2_contact",
        "scope_type": "plant",
        "scope_id": str(nis2_plant.id),
        "valid_from": str(timezone.localdate()),
    }
    r1 = client.post("/api/v1/governance/role-assignments/", payload, format="json")
    assert r1.status_code == 201
    r2 = client.post("/api/v1/governance/role-assignments/", payload, format="json")
    assert r2.status_code == 400
    assert "role" in r2.json()


@pytest.mark.django_db
def test_multi_holder_role_allows_duplicates(client, org_user, plain_plant):
    """Control Owner ammette più titolari sullo stesso sito."""
    u2 = User.objects.create_user(username="co2", email="co2@test.com", password="t")
    base = {
        "role": "control_owner", "scope_type": "plant", "scope_id": str(plain_plant.id),
        "valid_from": str(timezone.localdate()),
    }
    r1 = client.post("/api/v1/governance/role-assignments/", {**base, "user": org_user.id}, format="json")
    r2 = client.post("/api/v1/governance/role-assignments/", {**base, "user": u2.id}, format="json")
    assert r1.status_code == 201 and r2.status_code == 201


@pytest.mark.django_db
def test_is_single_holder_respects_requirement_override(db):
    from apps.governance.models import RoleRequirement
    from apps.governance.services import is_single_holder

    # control_owner di default è multi
    assert is_single_holder("control_owner") is False
    # ma un requisito può forzarlo a titolare unico
    RoleRequirement.objects.create(
        role="control_owner", scope_level="plant", mandatory=False, single_holder=True,
    )
    assert is_single_holder("control_owner") is True


@pytest.mark.django_db
def test_matrix_includes_all_non_org_roles_with_unset(org_user, plain_plant):
    """La matrice completa include i ruoli non obbligatori con stato 'unset'."""
    from apps.governance.services import get_role_coverage_matrix

    m = get_role_coverage_matrix(org_user)
    roles = {r["role"] for r in m["plant_roles"]}
    assert "control_owner" in roles and "plant_manager" in roles
    # ruolo non obbligatorio e senza titolare → unset (non 'vacant')
    co = _plant_row(m, "control_owner")
    assert co["required"] is False
    assert co["cells"][str(plain_plant.id)]["status"] == "unset"


@pytest.mark.django_db
def test_requirement_crud_and_audit(client):
    from core.audit import AuditLog

    payload = {"role": "plant_security_officer", "scope_level": "plant",
               "applies_to": "all", "org_covers_sites": False}
    resp = client.post(URL_REQUIREMENTS, payload, format="json")
    assert resp.status_code == 201
    rid = resp.json()["id"]
    assert AuditLog.objects.filter(action_code="governance.role_requirement.create").exists()

    resp = client.patch(f"{URL_REQUIREMENTS}{rid}/", {"enabled": False}, format="json")
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False

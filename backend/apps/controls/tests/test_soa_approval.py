"""
Test C5 — workflow di approvazione formale del SoA via UI/endpoint.

`bulk-approve-soa` approva formalmente un gruppo di controlli ISO 27001 (chi/
quando registrati), supporta la revoca (approved=false) e ignora i controlli di
framework non ISO (lo Statement of Applicability è un artefatto ISO 27001).
"""
import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL = "/api/v1/controls/instances/bulk-approve-soa/"


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(
        username="soa_user", email="soa@test.com", password="test",
        first_name="Sara", last_name="Rossi",
    )
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def make(db, user):
    from apps.controls.models import Control, ControlInstance, Framework
    from apps.plants.models import Plant, PlantFramework

    plant = Plant.objects.create(code="SOA-P", name="Plant SoA", country="IT",
                                 nis2_scope="non_soggetto", status="attivo")
    counter = {"n": 0}

    def _make(fw_code):
        counter["n"] += 1
        n = counter["n"]
        fw, _ = Framework.objects.get_or_create(
            code=fw_code, defaults={"name": fw_code, "version": "1", "published_at": timezone.localdate()},
        )
        PlantFramework.objects.get_or_create(
            plant=plant, framework=fw,
            defaults={"active_from": timezone.localdate(), "level": "L2", "active": True},
        )
        ctrl = Control.objects.create(
            framework=fw, external_id=f"{fw_code}-{n}",
            translations={"it": {"title": f"C{n}"}}, evidence_requirement={},
        )
        return ControlInstance.objects.create(plant=plant, control=ctrl, status="compliant", created_by=user)

    return _make


@pytest.mark.django_db
def test_approve_records_who_and_when(client, make, user):
    inst = make("ISO27001")
    resp = client.post(URL, {"instance_ids": [str(inst.id)]}, format="json")
    assert resp.status_code == 200
    assert resp.data["approved_count"] == 1

    inst.refresh_from_db()
    assert inst.approved_in_soa is True
    assert inst.soa_approved_by == user
    assert inst.soa_approved_at is not None


@pytest.mark.django_db
def test_revoke_clears_approval(client, make):
    inst = make("ISO27001")
    client.post(URL, {"instance_ids": [str(inst.id)]}, format="json")

    resp = client.post(URL, {"instance_ids": [str(inst.id)], "approved": False}, format="json")
    assert resp.status_code == 200
    assert resp.data["approved"] is False

    inst.refresh_from_db()
    assert inst.approved_in_soa is False
    assert inst.soa_approved_by is None
    assert inst.soa_approved_at is None


@pytest.mark.django_db
def test_non_iso_controls_are_ignored(client, make):
    """Il SoA è ISO 27001: un controllo NIS2 non viene approvato."""
    iso = make("ISO27001")
    nis2 = make("NIS2")
    resp = client.post(URL, {"instance_ids": [str(iso.id), str(nis2.id)]}, format="json")
    assert resp.status_code == 200
    assert resp.data["approved_count"] == 1  # solo ISO

    iso.refresh_from_db()
    nis2.refresh_from_db()
    assert iso.approved_in_soa is True
    assert nis2.approved_in_soa is False

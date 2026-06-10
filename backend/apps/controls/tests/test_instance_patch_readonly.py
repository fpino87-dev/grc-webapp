"""
Test C1 — i campi governati dai service non sono scrivibili via PATCH generica.

Prima del fix, PATCH /instances/{id}/ scriveva `status` (e approved_in_soa,
maturity_level, ...) direttamente sul model, bypassando evaluate_control():
compliant senza evidenze, N/A senza giustificazione, nessun audit
`control.evaluated`. Ora quei campi sono read_only nel serializer (la PATCH
li ignora, comportamento DRF standard) e l'unica via è l'endpoint dedicato.
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
    u = User.objects.create_user(username="ro_user", email="ro@test.com", password="test")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def instance(db, user):
    from apps.controls.models import Control, ControlInstance, Framework
    from apps.plants.models import Plant, PlantFramework

    plant = Plant.objects.create(
        code="RO-P", name="Plant ReadOnly", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )
    fw = Framework.objects.create(
        code="ISO-RO", name="ISO RO", version="2022",
        published_at=timezone.localdate(),
    )
    PlantFramework.objects.create(
        plant=plant, framework=fw,
        active_from=timezone.localdate(), level="L2", active=True,
    )
    control = Control.objects.create(
        framework=fw, external_id="RO-1.1",
        translations={"it": {"title": "Controllo RO"}},
        evidence_requirement={},
    )
    return ControlInstance.objects.create(
        plant=plant, control=control, status="non_valutato", created_by=user,
    )


@pytest.mark.django_db
def test_patch_status_is_ignored(client, instance):
    """PATCH con status non cambia lo stato e non genera audit di valutazione."""
    from core.audit import AuditLog

    resp = client.patch(
        f"{URL_INSTANCES}{instance.id}/", {"status": "compliant"}, format="json"
    )
    assert resp.status_code == 200
    instance.refresh_from_db()
    assert instance.status == "non_valutato"
    assert instance.last_evaluated_at is None
    assert not AuditLog.objects.filter(
        entity_id=instance.pk, action_code="control.evaluated"
    ).exists()


@pytest.mark.django_db
def test_patch_soa_and_maturity_are_ignored(client, instance):
    """Auto-approvazione SOA e override maturity via PATCH non passano."""
    resp = client.patch(
        f"{URL_INSTANCES}{instance.id}/",
        {
            "approved_in_soa": True,
            "soa_approved_at": "2026-06-10T10:00:00Z",
            "maturity_level": 5,
            "maturity_level_override": True,
            "applicability": "escluso",
            "na_justification": "x",
        },
        format="json",
    )
    assert resp.status_code == 200
    instance.refresh_from_db()
    assert instance.approved_in_soa is False
    assert instance.soa_approved_at is None
    assert instance.maturity_level_override is False
    assert instance.applicability != "escluso"
    assert instance.na_justification == ""


@pytest.mark.django_db
def test_patch_notes_and_owner_still_writable(client, instance, user):
    """I campi non governati (notes, owner) restano modificabili via PATCH."""
    resp = client.patch(
        f"{URL_INSTANCES}{instance.id}/",
        {"notes": "Nota operativa", "owner": user.id},
        format="json",
    )
    assert resp.status_code == 200
    instance.refresh_from_db()
    assert instance.notes == "Nota operativa"
    assert instance.owner_id == user.id


@pytest.mark.django_db
def test_evaluate_endpoint_remains_the_writing_path(client, instance):
    """POST /evaluate/ resta la via corretta: valida, scrive stato e audit."""
    from core.audit import AuditLog

    # 'na' senza giustificazione → respinto dal service
    resp = client.post(
        f"{URL_INSTANCES}{instance.id}/evaluate/",
        {"status": "na", "note": ""},
        format="json",
    )
    assert resp.status_code == 400

    # 'gap' non richiede evidenze → accettato, con audit e last_evaluated_at
    resp = client.post(
        f"{URL_INSTANCES}{instance.id}/evaluate/",
        {"status": "gap", "note": "Nessuna misura in atto"},
        format="json",
    )
    assert resp.status_code == 200
    instance.refresh_from_db()
    assert instance.status == "gap"
    assert instance.last_evaluated_at is not None
    assert AuditLog.objects.filter(
        entity_id=instance.pk, action_code="control.evaluated"
    ).exists()

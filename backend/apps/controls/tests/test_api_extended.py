"""Test API controlli — framework, domini, istanze."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_FRAMEWORKS = "/api/v1/controls/frameworks/"
URL_DOMAINS = "/api/v1/controls/domains/"
URL_CONTROLS = "/api/v1/controls/controls/"
URL_INSTANCES = "/api/v1/controls/instances/"


@pytest.fixture
def user(db):
    """Utente con scope org (vede tutte le control instances)."""
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="ctrl_user", email="ctrl@test.com", password="test")
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
        code="CT-P", name="Plant Controls", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def framework(db):
    from apps.controls.models import Framework
    from datetime import date
    return Framework.objects.create(
        code="ISO27001-TEST", name="ISO 27001 Test", version="2022",
        published_at=date.today(),
    )


@pytest.fixture
def domain(db, framework):
    from apps.controls.models import ControlDomain
    return ControlDomain.objects.create(
        framework=framework, code="A.5",
        translations={"it": {"name": "Politiche di sicurezza"}, "en": {"name": "Security policies"}},
        order=1,
    )


@pytest.fixture
def control(db, framework, domain):
    from apps.controls.models import Control
    return Control.objects.create(
        framework=framework,
        domain=domain,
        external_id="A.5.1",
        translations={"it": {"name": "Policy sicurezza", "description": "Desc"}, "en": {"name": "Security policy", "description": "Desc"}},
        level="L2",
        evidence_requirement={},
        control_category="technical",
    )


@pytest.fixture
def plant_framework(db, plant, framework, user):
    from apps.plants.models import PlantFramework
    from datetime import date
    return PlantFramework.objects.create(
        plant=plant, framework=framework,
        active_from=date.today(), level="L2", active=True,
    )


@pytest.fixture
def instance(db, plant, control, plant_framework, user):
    from apps.controls.models import ControlInstance
    return ControlInstance.objects.create(
        plant=plant,
        control=control,
        status="non_valutato",
        created_by=user,
    )


# ── Frameworks ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_frameworks_authenticated(client):
    resp = client.get(URL_FRAMEWORKS)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_list_frameworks_unauthenticated():
    resp = APIClient().get(URL_FRAMEWORKS)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_retrieve_framework(client, framework):
    resp = client.get(f"{URL_FRAMEWORKS}{framework.id}/")
    assert resp.status_code == 200
    assert resp.data["code"] == "ISO27001-TEST"


@pytest.mark.django_db
def test_create_framework(client):
    from datetime import date
    payload = {"code": "NIS2-TEST", "name": "NIS2 Test", "version": "2022", "published_at": str(date.today())}
    resp = client.post(URL_FRAMEWORKS, payload, format="json")
    assert resp.status_code == 201


# ── Domains ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_domains(client):
    resp = client.get(URL_DOMAINS)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_retrieve_domain(client, domain):
    resp = client.get(f"{URL_DOMAINS}{domain.id}/")
    assert resp.status_code == 200
    assert resp.data["code"] == "A.5"


@pytest.mark.django_db
def test_filter_domains_by_framework(client, framework, domain):
    resp = client.get(f"{URL_DOMAINS}?framework={framework.id}")
    assert resp.status_code == 200


# ── Controls ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_controls(client):
    resp = client.get(URL_CONTROLS)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_retrieve_control(client, control):
    resp = client.get(f"{URL_CONTROLS}{control.id}/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_filter_controls_by_framework(client, framework, control):
    resp = client.get(f"{URL_CONTROLS}?framework={framework.id}")
    assert resp.status_code == 200


# ── Control Instances ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_instances_authenticated(client):
    resp = client.get(URL_INSTANCES)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_retrieve_instance(client, instance):
    resp = client.get(f"{URL_INSTANCES}{instance.id}/")
    assert resp.status_code == 200
    assert resp.data["status"] == "non_valutato"


@pytest.mark.django_db
def test_create_instance(client, plant, control, plant_framework):
    payload = {
        "plant": str(plant.id),
        "control": str(control.id),
        "status": "non_valutato",
    }
    resp = client.post(URL_INSTANCES, payload, format="json")
    assert resp.status_code == 201


@pytest.mark.django_db
def test_update_instance_notes(client, instance):
    resp = client.patch(f"{URL_INSTANCES}{instance.id}/", {"notes": "Aggiornato"}, format="json")
    assert resp.status_code == 200
    assert resp.data["notes"] == "Aggiornato"


@pytest.mark.django_db
def test_delete_instance(client, instance):
    resp = client.delete(f"{URL_INSTANCES}{instance.id}/")
    assert resp.status_code == 204


@pytest.mark.django_db
def test_filter_instances_by_plant(client, plant, instance):
    resp = client.get(f"{URL_INSTANCES}?plant={plant.id}")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_filter_instances_by_status(client, instance):
    resp = client.get(f"{URL_INSTANCES}?status=non_valutato")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_instance_evaluate_action(client, instance):
    """evaluate endpoint should handle both valid and missing evidence cases."""
    resp = client.post(
        f"{URL_INSTANCES}{instance.id}/evaluate/",
        {"status": "non_conforme", "notes": "Test note"},
        format="json",
    )
    assert resp.status_code in (200, 400)


@pytest.mark.django_db
def test_instance_detail_info_action(client, instance):
    resp = client.get(f"{URL_INSTANCES}{instance.id}/detail-info/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_instance_set_applicability_action(client, instance):
    resp = client.post(
        f"{URL_INSTANCES}{instance.id}/set-applicability/",
        {"applicability": "applicable"},
        format="json",
    )
    assert resp.status_code in (200, 400)


@pytest.mark.django_db
def test_instance_set_maturity_action(client, instance):
    resp = client.post(
        f"{URL_INSTANCES}{instance.id}/set-maturity/",
        {"maturity_level": 3},
        format="json",
    )
    assert resp.status_code in (200, 400)


@pytest.mark.django_db
def test_instances_needs_revaluation_action(client):
    resp = client.get(f"{URL_INSTANCES}needs-revaluation/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_framework_governance_action(client, framework):
    resp = client.get(f"{URL_FRAMEWORKS}governance/")
    assert resp.status_code == 200


# ── RBAC plant scoping (S1) ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_pm_does_not_see_control_instance_of_other_plant(db, framework, control):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    from apps.controls.models import ControlInstance
    from apps.plants.models import Plant, PlantFramework
    from datetime import date

    plant_a = Plant.objects.create(
        code="CT-SC-A", name="A", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )
    plant_b = Plant.objects.create(
        code="CT-SC-B", name="B", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )
    PlantFramework.objects.create(plant=plant_a, framework=framework, active_from=date.today(), active=True)
    PlantFramework.objects.create(plant=plant_b, framework=framework, active_from=date.today(), active=True)
    ControlInstance.objects.create(plant=plant_a, control=control)
    ControlInstance.objects.create(plant=plant_b, control=control)

    pm = User.objects.create_user(username="pm_a_ctrl", email="pmctrl@test", password="x")
    access = UserPlantAccess.objects.create(
        user=pm, role=GrcRole.PLANT_MANAGER, scope_type="single_plant",
    )
    access.scope_plants.set([plant_a])

    c = APIClient()
    c.force_authenticate(user=pm)
    resp = c.get(URL_INSTANCES)
    assert resp.status_code == 200
    plant_ids = {str(item["plant"]) for item in resp.data["results"]}
    assert plant_ids == {str(plant_a.id)}

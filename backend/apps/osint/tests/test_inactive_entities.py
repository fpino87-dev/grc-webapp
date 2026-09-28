"""Finding di entità non più monitorate (dominio tolto dal sito, fornitore
cessato) fuori da coda, conteggi ed export; problemi dei fornitori solo
informativi: niente task interni."""
import uuid

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.osint.models import EntityType, OsintEntity, OsintFinding, SourceModule

User = get_user_model()
pytestmark = pytest.mark.django_db
URL = "/api/v1/osint/findings/"


@pytest.fixture
def client(db):
    u = User.objects.create_superuser(username="osinact", password="x", email="osinact@test.com")
    c = APIClient()
    c.force_authenticate(user=u)
    return c


def _entity(kind, domain, active=True):
    module = SourceModule.SUPPLIERS if kind == EntityType.SUPPLIER else SourceModule.SITES
    return OsintEntity.objects.create(entity_type=kind, source_module=module, source_id=uuid.uuid4(),
                                      domain=domain, display_name=domain, is_active=active)


def _finding(entity, severity="critical"):
    return OsintFinding.objects.create(entity=entity, code="ssl_expired", severity=severity)


def test_findings_of_deactivated_domain_leave_the_queue_and_come_back(client):
    live = _entity(EntityType.MY_DOMAIN, "attivo.example.com")
    gone = _entity(EntityType.MY_DOMAIN, "tolto.example.com", active=False)
    f_live, f_gone = _finding(live), _finding(gone)

    ids = {r["id"] for r in client.get(URL, {"ownership": "own", "open_only": "1"}).data}
    assert ids == {str(f_live.pk)}
    assert client.get(f"{URL}summary/", {"ownership": "own"}).data["open_critical"] == 1
    assert client.get(f"{URL}{f_gone.pk}/").status_code == 404

    gone.is_active = True
    gone.save()
    ids = {r["id"] for r in client.get(URL, {"ownership": "own", "open_only": "1"}).data}
    assert ids == {str(f_live.pk), str(f_gone.pk)}


def test_supplier_finding_never_becomes_internal_task(client):
    from apps.tasks.models import Task

    sup = _finding(_entity(EntityType.SUPPLIER, "fornitore.example.com"))
    own = _finding(_entity(EntityType.MY_DOMAIN, "nostro.example.com"))
    assert client.post(f"{URL}{sup.pk}/create-task/").status_code == 400
    resp = client.post(f"{URL}bulk-task/", {"finding_ids": [str(sup.pk), str(own.pk)]}, format="json")
    assert resp.data["created"] == 1
    assert not Task.objects.filter(source_module="osint", source_id=sup.pk).exists()
    assert Task.objects.filter(source_module="osint", source_id=own.pk).exists()

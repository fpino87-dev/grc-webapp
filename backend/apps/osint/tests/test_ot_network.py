"""P2-2 — sblocco automazioni OSINT su AssetOT.

Copre:
- `_sync_assets_ot`: gli AssetOT con interfaccia pubblica (fqdn/ip) diventano
  entità OSINT; quelli senza campi di rete restano fuori.
- `_has_ot_asset_linked` + routing: un alert CRITICAL su un fornitore che
  manutiene asset OT va in PENDING_ESCALATION invece di generare un Task.
"""
from unittest.mock import patch

import pytest

from apps.assets.models import AssetOT
from apps.osint.alerts import _has_ot_asset_linked, run_alerts
from apps.osint.models import (
    AlertSeverity,
    AlertStatus,
    EntityType,
    OsintEntity,
    OsintScan,
    OsintSettings,
    ScanStatus,
    SourceModule,
)
from apps.osint.services import aggregate_entities
from apps.plants.models import Plant
from apps.suppliers.models import Supplier

pytestmark = pytest.mark.django_db


@pytest.fixture
def plant(db):
    return Plant.objects.create(
        code="OTP1", name="OT Plant", country="IT",
        nis2_scope="essenziale", status="attivo",
    )


# ── _sync_assets_ot ─────────────────────────────────────────────────────────


def test_sync_assets_ot_public_interface_creates_entity(plant):
    AssetOT.objects.create(
        plant=plant, name="HMI esposta", asset_type="OT",
        purdue_level=2, category="HMI",
        fqdn="hmi.plant.example.com", internet_exposed=True,
    )
    with patch("apps.osint.validators.is_public_internet_target", return_value=True):
        aggregate_entities()

    ents = OsintEntity.objects.filter(source_module=SourceModule.ASSETS_OT)
    assert ents.count() == 1
    e = ents.first()
    assert e.domain == "hmi.plant.example.com"
    assert e.entity_type == EntityType.ASSET


def test_sync_assets_ot_fqdn_and_ip(plant):
    AssetOT.objects.create(
        plant=plant, name="PLC mgmt", asset_type="OT",
        purdue_level=1, category="PLC",
        fqdn="plc.plant.example.com", ip_address="203.0.113.20",
        internet_exposed=True,
    )
    with patch("apps.osint.validators.is_public_internet_target", return_value=True):
        aggregate_entities()

    domains = set(
        OsintEntity.objects.filter(source_module=SourceModule.ASSETS_OT)
        .values_list("domain", flat=True)
    )
    assert domains == {"plc.plant.example.com", "203.0.113.20"}


def test_sync_assets_ot_without_network_fields_no_entity(plant):
    AssetOT.objects.create(
        plant=plant, name="PLC interno", asset_type="OT",
        purdue_level=1, category="PLC",
    )
    aggregate_entities()
    assert OsintEntity.objects.filter(source_module=SourceModule.ASSETS_OT).count() == 0


def test_sync_assets_ot_non_public_skipped(plant):
    AssetOT.objects.create(
        plant=plant, name="PLC LAN", asset_type="OT",
        purdue_level=1, category="PLC", fqdn="plc.internal.local",
    )
    # is_public_internet_target reale → un .local non è target pubblico valido
    aggregate_entities()
    assert OsintEntity.objects.filter(source_module=SourceModule.ASSETS_OT).count() == 0


# ── _has_ot_asset_linked ────────────────────────────────────────────────────


def _supplier_entity(supplier):
    return OsintEntity.objects.create(
        entity_type=EntityType.SUPPLIER,
        source_module=SourceModule.SUPPLIERS,
        source_id=supplier.id,
        domain="supplier.example.com",
        display_name=supplier.name,
        is_nis2_critical=True,
    )


def test_has_ot_asset_linked_true_when_maintains_ot(plant):
    sup = Supplier.objects.create(name="Teleassistenza Srl")
    AssetOT.objects.create(
        plant=plant, name="Macchina X", asset_type="OT",
        purdue_level=2, category="SCADA", maintainer_supplier=sup,
    )
    assert _has_ot_asset_linked(_supplier_entity(sup)) is True


def test_has_ot_asset_linked_false_without_link(plant):
    sup = Supplier.objects.create(name="Fornitore generico")
    assert _has_ot_asset_linked(_supplier_entity(sup)) is False


def test_has_ot_asset_linked_ignores_soft_deleted_asset(plant):
    sup = Supplier.objects.create(name="Teleassistenza Srl")
    asset = AssetOT.objects.create(
        plant=plant, name="Macchina Y", asset_type="OT",
        purdue_level=2, category="SCADA", maintainer_supplier=sup,
    )
    asset.soft_delete()
    assert _has_ot_asset_linked(_supplier_entity(sup)) is False


def test_has_ot_asset_linked_false_for_non_supplier_module(plant):
    sup = Supplier.objects.create(name="X")
    AssetOT.objects.create(
        plant=plant, name="Macchina Z", asset_type="OT",
        purdue_level=2, category="SCADA", maintainer_supplier=sup,
    )
    ent = OsintEntity.objects.create(
        entity_type=EntityType.ASSET,
        source_module=SourceModule.ASSETS_IT,
        source_id=sup.id,  # stesso UUID, ma modulo sbagliato
        domain="x.example.com", display_name="X", is_nis2_critical=False,
    )
    assert _has_ot_asset_linked(ent) is False


# ── routing: escalation invece di Task ──────────────────────────────────────


def _critical_scan(entity):
    return OsintScan.objects.create(
        entity=entity, status=ScanStatus.COMPLETED,
        ssl_valid=False, ssl_days_remaining=None, score_total=10,
    )


def test_critical_supplier_with_ot_escalates_not_task(plant):
    s = OsintSettings.load()
    sup = Supplier.objects.create(name="Teleassistenza Srl")
    AssetOT.objects.create(
        plant=plant, name="Macchina X", asset_type="OT",
        purdue_level=2, category="SCADA", maintainer_supplier=sup,
    )
    entity = _supplier_entity(sup)
    scan = _critical_scan(entity)

    from apps.tasks.models import Task
    task_before = Task.objects.count()
    run_alerts(entity, scan, s)

    # Nessun task auto-creato; l'alert critico è in attesa di escalation umana.
    assert Task.objects.count() == task_before
    crit = entity.alerts.filter(severity=AlertSeverity.CRITICAL).first()
    assert crit is not None
    assert crit.status == AlertStatus.PENDING_ESCALATION


def test_critical_supplier_without_ot_creates_task(plant):
    s = OsintSettings.load()
    sup = Supplier.objects.create(name="Fornitore senza OT")
    entity = _supplier_entity(sup)
    scan = _critical_scan(entity)

    from apps.tasks.models import Task
    task_before = Task.objects.count()
    run_alerts(entity, scan, s)
    assert Task.objects.count() > task_before

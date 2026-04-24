"""Test Step 2 — aggregator OSINT."""
import pytest

from apps.assets.models import AssetIT, AssetSW
from apps.osint.models import (
    EntityType,
    OsintEntity,
    OsintSettings,
    SourceModule,
)
from apps.osint.services import aggregate_entities, extract_domain, find_duplicates
from apps.plants.models import Plant
from apps.suppliers.models import Supplier


pytestmark = pytest.mark.django_db


class TestExtractDomain:
    def test_empty(self):
        assert extract_domain("") == ""
        assert extract_domain(None) == ""

    def test_plain_domain(self):
        assert extract_domain("Example.COM") == "example.com"

    def test_with_scheme(self):
        assert extract_domain("https://example.com/path") == "example.com"
        assert extract_domain("http://sub.example.com:8080/x") == "sub.example.com"

    def test_trailing_dot(self):
        assert extract_domain("example.com.") == "example.com"

    def test_whitespace(self):
        assert extract_domain("  example.com  ") == "example.com"


class TestAggregator:
    def test_plants_primary_and_additional_domains(self):
        p = Plant.objects.create(
            code="P1",
            name="Plant One",
            country="IT",
            nis2_scope="essenziale",
            status="attivo",
            domain="azienda.it",
            additional_domains=["plant-milano.azienda.it", "sede-roma.azienda.it"],
        )
        res = aggregate_entities()
        assert res.created == 3
        assert OsintEntity.objects.count() == 3
        ent = OsintEntity.objects.filter(source_id=p.id, domain="azienda.it").first()
        assert ent is not None
        assert ent.entity_type == EntityType.MY_DOMAIN
        assert ent.is_nis2_critical is True  # NIS2 essenziale
        assert ent.source_module == SourceModule.SITES

    def test_idempotent(self):
        Plant.objects.create(
            code="P1", name="P1", country="IT",
            nis2_scope="non_soggetto", status="attivo",
            domain="a.com",
        )
        aggregate_entities()
        res2 = aggregate_entities()
        assert res2.created == 0
        assert res2.updated == 0
        assert OsintEntity.objects.count() == 1

    def test_plant_name_change_propagates(self):
        p = Plant.objects.create(
            code="P1", name="Old", country="IT",
            nis2_scope="non_soggetto", status="attivo", domain="a.com",
        )
        aggregate_entities()
        p.name = "New"
        p.save()
        res = aggregate_entities()
        assert res.updated == 1
        assert OsintEntity.objects.get(source_id=p.id).display_name == "New"

    def test_plant_soft_deleted_deactivates_entity(self):
        p = Plant.objects.create(
            code="P1", name="P1", country="IT",
            nis2_scope="non_soggetto", status="attivo", domain="a.com",
        )
        aggregate_entities()
        assert OsintEntity.objects.get(source_id=p.id).is_active is True
        p.soft_delete()
        res = aggregate_entities()
        assert res.deactivated == 1
        e = OsintEntity.objects.get(source_id=p.id)
        assert e.is_active is False

    def test_suppliers_with_website(self):
        Supplier.objects.create(
            name="Acme", website="https://acme.example.com",
            nis2_relevant=True,
        )
        Supplier.objects.create(name="NoSite")  # no website → skipped
        res = aggregate_entities()
        assert res.created == 1
        e = OsintEntity.objects.get(source_module=SourceModule.SUPPLIERS)
        assert e.entity_type == EntityType.SUPPLIER
        assert e.domain == "acme.example.com"
        assert e.is_nis2_critical is True

    def test_assets_it_fqdn_and_ip(self, plant_nis2):
        AssetIT.objects.create(
            plant=plant_nis2, name="Web01", asset_type="IT",
            fqdn="web01.corp.example.com", ip_address="203.0.113.10",
        )
        res = aggregate_entities()
        # Plant ha niente domain → 0 da plants. AssetIT ha 2 entry (fqdn + ip).
        domains = set(
            OsintEntity.objects.filter(source_module=SourceModule.ASSETS_IT).values_list("domain", flat=True)
        )
        assert domains == {"web01.corp.example.com", "203.0.113.10"}

    def test_asset_sw_vendor_url(self, plant_nis2):
        AssetSW.objects.create(
            plant=plant_nis2, name="Office365", asset_type="SW",
            vendor="Microsoft", vendor_url="https://www.microsoft.com",
        )
        aggregate_entities()
        e = OsintEntity.objects.get(source_module=SourceModule.ASSETS_SOFTWARE)
        assert e.domain == "www.microsoft.com"
        assert e.entity_type == EntityType.SUPPLIER  # vendor = supplier-like

    def test_duplicate_domain_across_modules(self, plant_nis2):
        # Stesso dominio da Plant e da Supplier — deve creare 2 entità (una per modulo)
        plant_nis2.domain = "shared.example.com"
        plant_nis2.save()
        Supplier.objects.create(name="Sup", website="https://shared.example.com")
        aggregate_entities()
        dups = find_duplicates()
        assert "shared.example.com" in dups
        assert len(dups["shared.example.com"]) == 2

    def test_scan_frequency_respects_settings(self):
        s = OsintSettings.load()
        s.freq_my_domains = "monthly"
        s.save()
        Plant.objects.create(
            code="P1", name="P", country="IT",
            nis2_scope="non_soggetto", status="attivo", domain="a.com",
        )
        aggregate_entities()
        e = OsintEntity.objects.get(domain="a.com")
        assert e.scan_frequency == "monthly"

    def test_settings_singleton(self):
        s1 = OsintSettings.load()
        s2 = OsintSettings.load()
        assert s1.pk == s2.pk

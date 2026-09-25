"""KPI OSINT come connettori interni: postura esterna, critici aperti (domini
e asset del sito), fornitori critici a rischio."""
import datetime
import uuid

import pytest

from apps.osint.models import OsintEntity, OsintFinding, SourceModule
from apps.plants.models import Plant

pytestmark = pytest.mark.django_db
WEEK = datetime.date(2026, 9, 21)


def _plant(code):
    return Plant.objects.create(code=code, name=code, country="IT", nis2_scope="essenziale", status="attivo")


def _entity(kind, source_id, risk=None, deep=False, domain=None):
    module = {"my_domain": SourceModule.SITES, "asset": SourceModule.ASSETS_IT, "supplier": SourceModule.SUPPLIERS}[kind]
    return OsintEntity.objects.create(entity_type=kind, source_module=module, source_id=source_id,
                                      domain=domain or f"{uuid.uuid4().hex[:8]}.example.com", display_name="x",
                                      last_score_total=risk, deep_monitoring=deep)


def test_security_score_and_critical_count_cover_site_domains_and_assets():
    from apps.assets.models import AssetIT
    from apps.tasks.kpi_connectors import osint_critical_open_count, osint_security_score
    pa, pb = _plant("KA"), _plant("KB")
    asset = AssetIT.objects.create(plant=pa, name="Portale", asset_type="IT")
    dom = _entity("my_domain", pa.pk, risk=20)
    ast = _entity("asset", asset.pk, risk=60)
    _entity("my_domain", pb.pk, risk=0)
    OsintFinding.objects.create(entity=dom, code="ssl_expired", severity="critical")
    OsintFinding.objects.create(entity=ast, code="blacklist", severity="critical", status="resolved")
    OsintFinding.objects.create(entity=ast, code="dkim_missing", severity="warning")
    assert osint_security_score(pa, WEEK)["value"] == 60.0  # (80 + 40) / 2
    assert osint_critical_open_count(pa, WEEK)["value"] == 1.0
    assert osint_critical_open_count(pb, WEEK)["value"] == 0.0
    assert osint_security_score(_plant("KC"), WEEK)["value"] is None


def test_critical_suppliers_at_risk_rate_by_site():
    from apps.suppliers.models import Supplier
    from apps.tasks.kpi_connectors import osint_critical_suppliers_at_risk_rate
    pa = _plant("KS")
    s1, s2, s3 = (Supplier.objects.create(name=f"S{i}") for i in range(3))
    for s in (s1, s2, s3):
        s.plants.add(pa)
    _entity("supplier", s1.pk, risk=80, deep=True)   # F
    _entity("supplier", s2.pk, risk=10, deep=True)   # A/B
    _entity("supplier", s3.pk, risk=90, deep=False)  # non critico: escluso
    res = osint_critical_suppliers_at_risk_rate(pa, WEEK)
    assert res["value"] == 50.0 and res["run_count"] == 2
    # un fornitore senza siti serve tutta l'organizzazione: conta per ogni sito
    s4 = Supplier.objects.create(name="Org-wide")
    _entity("supplier", s4.pk, risk=85, deep=True)
    assert osint_critical_suppliers_at_risk_rate(pa, WEEK)["run_count"] == 3
    assert osint_critical_suppliers_at_risk_rate(_plant("KZ"), WEEK)["run_count"] == 1


def test_catalog_marks_osint_kpis_internal():
    from apps.tasks.kpi_catalog import KPI_CATALOG
    for code in ("osint_security_score", "osint_critical_open_count", "osint_critical_suppliers_at_risk_rate"):
        assert KPI_CATALOG[code]["source"] == "internal"

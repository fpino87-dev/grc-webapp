"""Test P2-3 — bridge OSINT → KPI engine M08 (osint_critical_open_count)."""
import pytest

from apps.osint.services import (
    OSINT_CRITICAL_KPI_CODE,
    count_open_critical_findings_by_plant,
    push_osint_kpis,
)
from apps.osint.models import (
    AlertSeverity, EntityType, FindingStatus, OsintEntity, OsintFinding,
    SourceModule,
)
from apps.plants.models import Plant


pytestmark = pytest.mark.django_db


def _plant(code):
    return Plant.objects.create(code=code, name=f"Plant {code}", country="IT",
                                nis2_scope="essenziale", status="attivo")


def _entity(plant, entity_type=EntityType.MY_DOMAIN, domain="d.example.com"):
    return OsintEntity.objects.create(
        entity_type=entity_type,
        source_module=SourceModule.SITES if entity_type == EntityType.MY_DOMAIN else SourceModule.SUPPLIERS,
        source_id=plant.id, domain=domain, display_name=domain,
    )


def _finding(entity, code="ssl_expired", severity=AlertSeverity.CRITICAL, status=FindingStatus.OPEN):
    return OsintFinding.objects.create(entity=entity, code=code, severity=severity, status=status)


class TestCount:
    def test_counts_open_critical_for_my_domain(self):
        p = _plant("C1")
        e = _entity(p)
        _finding(e, code="ssl_expired", severity=AlertSeverity.CRITICAL)
        _finding(e, code="blacklist", severity=AlertSeverity.CRITICAL)
        counts = count_open_critical_findings_by_plant()
        assert counts[str(p.id)] == 2

    def test_resolved_and_warning_excluded(self):
        p = _plant("C2")
        e = _entity(p)
        _finding(e, code="ssl_expired", severity=AlertSeverity.CRITICAL, status=FindingStatus.RESOLVED)
        _finding(e, code="dmarc_missing", severity=AlertSeverity.WARNING)
        counts = count_open_critical_findings_by_plant()
        assert counts[str(p.id)] == 0

    def test_plant_with_entity_but_no_critical_reported_as_zero(self):
        # Il plant compare con 0 così il KPI rientra quando l'esposizione si chiude.
        p = _plant("C3")
        _entity(p)
        counts = count_open_critical_findings_by_plant()
        assert counts[str(p.id)] == 0

    def test_supplier_findings_excluded(self):
        p = _plant("C4")
        sup = _entity(p, entity_type=EntityType.SUPPLIER, domain="sup.example.com")
        _finding(sup, severity=AlertSeverity.CRITICAL)
        counts = count_open_critical_findings_by_plant()
        # nessuna entità my_domain → plant non presente
        assert str(p.id) not in counts


class TestPush:
    def test_push_creates_kpi_snapshot(self):
        from apps.tasks.models import KPIDefinition, OperationalKpiSnapshot

        p = _plant("P1")
        e = _entity(p)
        _finding(e, severity=AlertSeverity.CRITICAL)

        result = push_osint_kpis()
        assert result["pushed"] == 1

        kpi = KPIDefinition.objects.get(kpi_code=OSINT_CRITICAL_KPI_CODE)
        # La definizione ha soglie (altrimenti lo status sarebbe sempre 'ok').
        assert kpi.threshold_direction == "below"
        assert kpi.threshold_warning == 0 and kpi.threshold_critical == 2
        snap = OperationalKpiSnapshot.objects.get(kpi_definition=kpi, plant=p)
        assert snap.value == 1
        assert snap.source == "api"  # ingest_kpi_from_api normalizza la sorgente
        assert snap.status == "warning"  # 1 finding critico aperto → warning (non 'ok')

    def test_push_three_criticals_is_critical_status(self):
        from apps.tasks.models import KPIDefinition, OperationalKpiSnapshot

        p = _plant("P3")
        e = _entity(p)
        for code in ("ssl_expired", "blacklist", "breach"):
            _finding(e, code=code, severity=AlertSeverity.CRITICAL)
        push_osint_kpis()
        kpi = KPIDefinition.objects.get(kpi_code=OSINT_CRITICAL_KPI_CODE)
        snap = OperationalKpiSnapshot.objects.get(kpi_definition=kpi, plant=p)
        assert snap.value == 3
        assert snap.status == "critical"  # ≥3 → critical

    def test_push_reports_zero_when_no_exposure(self):
        from apps.tasks.models import KPIDefinition, OperationalKpiSnapshot

        p = _plant("P2")
        _entity(p)  # entità ma nessun finding critico
        push_osint_kpis()
        kpi = KPIDefinition.objects.get(kpi_code=OSINT_CRITICAL_KPI_CODE)
        snap = OperationalKpiSnapshot.objects.get(kpi_definition=kpi, plant=p)
        assert snap.value == 0
        assert snap.status == "ok"  # 0 critici → ok

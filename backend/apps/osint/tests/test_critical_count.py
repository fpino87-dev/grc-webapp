"""Conteggio dei critici OSINT aperti per sito (usato dal Centro Operativo).
I KPI OSINT sono ora connettori interni: vedi apps/tasks/tests/test_kpi_osint.py."""
import pytest

from apps.osint.services import count_open_critical_findings_by_plant
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

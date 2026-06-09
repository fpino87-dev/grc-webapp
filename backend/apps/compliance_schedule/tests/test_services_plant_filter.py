"""Regressione: get_activity_schedule(plant=...) sui fornitori.

Supplier ha una M2M `plants` (non un FK `plant`): in passato i rami
"contratti fornitori" e "assessment fornitori" filtravano per `plant` →
FieldError/ValueError catturati e loggati, con le scadenze fornitori
silenziosamente NON calcolate. Questo test esercita esattamente quel
percorso e verifica che le voci compaiano senza errori.
"""
from datetime import timedelta

import pytest
from django.utils import timezone


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="CS-PF", name="Plant PF", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.mark.django_db
def test_activity_schedule_includes_supplier_for_plant(plant):
    from apps.suppliers.models import Supplier, SupplierAssessment
    from apps.compliance_schedule.services import get_activity_schedule

    due = timezone.localdate() + timedelta(days=10)

    sup = Supplier.objects.create(name="ACME Fornitore", risk_level="medio", status="attivo", evaluation_date=due)
    sup.plants.add(plant)
    SupplierAssessment.objects.create(
        supplier=sup, status="attivo",
        assessment_date=timezone.localdate(), next_assessment_date=due,
    )

    # Non deve sollevare e deve includere sia il contratto sia l'assessment.
    activities = get_activity_schedule(plant=plant)
    categories = {a["category"] for a in activities}
    assert "supplier_contract_review" in categories
    assert "supplier_assessment" in categories


@pytest.mark.django_db
def test_activity_schedule_excludes_supplier_of_other_plant(plant):
    """Un fornitore legato a un altro plant non compare nello schedule del plant."""
    from apps.plants.models import Plant
    from apps.suppliers.models import Supplier
    from apps.compliance_schedule.services import get_activity_schedule

    other = Plant.objects.create(code="CS-PF2", name="Plant PF2", country="IT",
                                 nis2_scope="non_soggetto", status="attivo")
    due = timezone.localdate() + timedelta(days=10)
    sup = Supplier.objects.create(name="Altro Fornitore", risk_level="medio", status="attivo", evaluation_date=due)
    sup.plants.add(other)

    labels = {a["label"] for a in get_activity_schedule(plant=plant)}
    assert "Contratto: Altro Fornitore" not in labels

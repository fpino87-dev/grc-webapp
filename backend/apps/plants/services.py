from django.db.models import QuerySet

from .models import Plant


def get_active_frameworks(plant):
    """
    Restituisce i Framework attivi per un plant.
    Se plant è None restituisce tutti i framework non archiviati.
    """
    from apps.controls.models import Framework
    if plant is None:
        return Framework.objects.filter(archived_at__isnull=True)
    return Framework.objects.filter(
        plantframework__plant=plant,
        plantframework__active=True,
        archived_at__isnull=True,
    ).distinct()


def get_active_framework_codes(plant) -> list:
    """Restituisce lista di codici framework attivi per il plant."""
    return list(get_active_frameworks(plant).values_list("code", flat=True))


def get_nis2_plants() -> QuerySet[Plant]:
    return Plant.objects.filter(nis2_scope__in=["essenziale", "importante"], deleted_at__isnull=True)

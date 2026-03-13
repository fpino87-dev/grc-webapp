from django.db.models import QuerySet

from .models import Plant


def get_nis2_plants() -> QuerySet[Plant]:
    return Plant.objects.filter(nis2_scope__in=["essenziale", "importante"], deleted_at__isnull=True)


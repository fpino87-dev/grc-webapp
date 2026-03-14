from django.utils import timezone
from .models import Supplier


def get_expiring_contracts(days: int = 60):
    """Return suppliers whose contract expires within the given number of days."""
    from django.utils import timezone
    import datetime

    today = timezone.now().date()
    deadline = today + datetime.timedelta(days=days)
    return Supplier.objects.filter(
        status="attivo",
        contract_expiry__isnull=False,
        contract_expiry__lte=deadline,
        contract_expiry__gte=today,
    )


def get_high_risk_suppliers():
    """Return suppliers with risk_level alto or critico."""
    return Supplier.objects.filter(risk_level__in=["alto", "critico"], status="attivo")

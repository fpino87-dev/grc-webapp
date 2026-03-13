from typing import Optional

from django.contrib.auth import get_user_model

from apps.plants.models import Plant
from .models import GrcRole, UserPlantAccess


def resolve_current_risk_manager(plant: Plant) -> Optional[get_user_model()]:
    """
    Esempio di risoluzione dinamica del ruolo su plant.
    """
    access = (
        UserPlantAccess.objects.filter(
            role=GrcRole.RISK_MANAGER,
            scope_type__in=["org", "single_plant", "plant_list"],
            deleted_at__isnull=True,
        )
        .select_related("user")
        .first()
    )
    return access.user if access else None


from django.core.exceptions import ValidationError
from django.utils import timezone

from core.audit import log_action
from .models import Incident


def close_incident(incident: Incident, user):
    try:
        rca = incident.rca
    except Exception:
        rca = None
    if rca is None or rca.approved_at is None:
        raise ValidationError("RCA approvato obbligatorio per chiudere l'incidente.")
    incident.status = "chiuso"
    incident.closed_at = timezone.now()
    incident.closed_by = user
    incident.save()
    log_action(
        user=user,
        action_code="incidents.close",
        level="L2",
        entity=incident,
        payload={"incident_id": str(incident.id)},
    )
    # Feed automatico verso M12 e M11 da implementare nei rispettivi moduli


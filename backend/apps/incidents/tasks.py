from celery import shared_task

from core.audit import log_action
from .models import Incident


@shared_task
def nis2_confirmation_check(incident_id):
    """Dopo 30 minuti: se ancora da_valutare assume sì."""
    inc = Incident.objects.filter(pk=incident_id, nis2_notifiable="da_valutare").first()
    if inc:
        inc.nis2_notifiable = "si"
        inc.save(update_fields=["nis2_notifiable"])
        # livello L1 per evento operativo
        # user è opzionale qui; si può usare un utente di sistema se configurato
        log_action(
            user=getattr(inc, "created_by", None),
            action_code="incidents.nis2_auto_confirm",
            level="L1",
            entity=inc,
            payload={"incident_id": str(inc.id), "auto_confirm": True},
        )


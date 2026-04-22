from celery import shared_task


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, default_retry_delay=120)
def check_questionnaire_followups_task(self):
    from .services import check_questionnaire_followups
    check_questionnaire_followups()


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, default_retry_delay=300)
def recompute_expired_risk_adj_task(self):
    """Nightly: ricalcola risk_adj per tutti i fornitori attivi.
    Cattura assessment esterni appena scaduti che non devono più partecipare al worst-case."""
    from .risk_adj import recompute_expired_risk_adj
    return recompute_expired_risk_adj()

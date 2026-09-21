from celery import shared_task


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, default_retry_delay=120)
def remind_training_plan_items_task(self):
    """Promemoria giornaliero delle voci del piano formativo in scadenza o in
    ritardo. Ritorna solo conteggi (regola #11)."""
    from .services import remind_plan_items

    return remind_plan_items()

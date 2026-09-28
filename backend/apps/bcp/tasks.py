from celery import shared_task

from . import services


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def check_expired_bcp_plans():
    """Piani BCP approvati con test scaduto o mai eseguito: un task al Risk
    Manager per piano (uno solo finché resta aperto).

    Il piano resta approvato: un test scaduto rende i processi "scoperti per
    test scaduto" (bcp.services.process_coverage), non li lascia senza piano.
    """
    created = services.open_overdue_test_tasks()
    return f"check_expired_bcp_plans: {created} task creati"

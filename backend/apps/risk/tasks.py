from celery import shared_task


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def check_risk_treatments():
    """Giornaliero: accettazioni in scadenza o scadute e misure del piano di
    trattamento in ritardo, con escalation secondo la policy (procedura §10, §11.3)."""
    from .services import escalate_overdue_plans, expire_acceptances

    acceptances = expire_acceptances()
    plans = escalate_overdue_plans()
    return (
        f"check_risk_treatments: accettazioni {acceptances['warned']} in scadenza, "
        f"{acceptances['expired']} scadute; misure {plans['notified']} in ritardo, "
        f"{plans['escalated']} in escalation"
    )

from celery import shared_task


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, default_retry_delay=120)
def check_questionnaire_followups_task(self):
    from .services import check_questionnaire_followups
    check_questionnaire_followups()
